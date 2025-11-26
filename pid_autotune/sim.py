#!/bin/python3

from pid_autotune.pid import PIDArduino
from pid_autotune.autotune import PIDAutotune
from pid_autotune.kettle import Kettle
from collections import deque, namedtuple
import sys
import math
import logging
import matplotlib.pyplot as plt
from typing import Dict


LOG_FORMAT = '%(name)s: %(message)s'
Simulation = namedtuple(
    'Simulation',
    ['name', 'sut', 'kettle', 'delayed_temps', 'timestamps',
     'heater_temps', 'sensor_temps', 'outputs'])
Arg_nt = namedtuple("Args", ["pid", "autotune", "verbose", "export", "noplot", 
                             "kettle_temp", "setpoint", "ambient_temp", "interval", 
                             "delay", "sampletime", "volume", "diameter", 
                             "heater_power", "heat_loss_factor", "out_min", "out_max", 
                             "json_output"])

def write_csv(sim):
    filename = sim.name + '.csv'
    with open(filename, 'w+') as csv:
        csv.write('timestamp;output;sensor_temp;heater_temp\n')

        for i in range(0, len(sim.timestamps)):
            csv.write('{0};{1:.2f};{2:.2f};{3:.2f}\n'.format(
                sim.timestamps[i], sim.outputs[i], sim.sensor_temps[i], sim.heater_temps[i]))

def generate_result_by_sims(sims):
    return {sim.name: 
            {
                'data': {
                    'timestamp': sim.timestamps,
                    'output': [x for x in sim.outputs],
                    'sensor_temp': [x for x in sim.sensor_temps], 
                    'heater_temp': [x for x in sim.heater_temps]
                }
            }
        for sim in sims}


def sim_update(sim, timestamp, output, args):
    sim.kettle.heat(args.heater_power * (output / 100), args.sampletime)
    sim.kettle.cool(args.sampletime, args.ambient_temp, args.heat_loss_factor)
    sim.delayed_temps.append(sim.kettle.temperature)
    sim.timestamps.append(timestamp)
    sim.outputs.append(output)
    sim.sensor_temps.append(sim.delayed_temps[0])
    sim.heater_temps.append(sim.kettle.temperature)


def plot_simulations(args, simulations, title):
    lines = []
    fig, ax1 = plt.subplots()
    upper_limit = 0

    # Try to limit the y-axis to a more relevant area if possible
    for sim in simulations:
        m = max(sim.sensor_temps) + 1
        upper_limit = max(upper_limit, m)

    if upper_limit > args.setpoint:
        lower_limit = args.setpoint - (upper_limit - args.setpoint)
        ax1.set_ylim(lower_limit, upper_limit)

    # Create x-axis and first y-axis (temperature)
    ax1.plot()
    ax1.set_xlabel('time (s)')
    ax1.set_ylabel('temperature (°C)')
    ax1.grid(axis='y', linestyle=':', alpha=0.5)

    # Draw setpoint line
    lines += [plt.axhline(
        y=args.setpoint, color='r', linestyle=':', linewidth=0.9, label='setpoint')]

    # Create second y-axis (power)
    ax2 = ax1.twinx()
    ax2.set_ylabel('power (%)')

    # Plot temperature and output values
    i = 0
    for sim in simulations:
        color_cycle_idx = 'C' + str(i)
        lines += ax1.plot(
            sim.timestamps, sim.sensor_temps, color=color_cycle_idx,
            alpha=1.0, label='{0}: temp.'.format(sim.name))
        lines += ax2.plot(
            sim.timestamps, sim.outputs, '--', color=color_cycle_idx,
            linewidth=1, alpha=0.7, label='{0}: output'.format(sim.name))
        i += 1

    # Create legend
    labels = [l.get_label() for l in lines]
    offset = math.ceil((1 + len(simulations) * 2) / 3) * 0.05
    ax1.legend(lines, labels, loc=9, bbox_to_anchor=(
        0.5, -0.1 - offset), ncol=3)
    fig.subplots_adjust(bottom=0.2 + offset)

    # Set title
    plt.title(title)
    # fig.canvas.set_window_title(title)
    plt.show()


def simulate_autotune(args):
    timestamp = 0  # seconds
    maxlen = max(1, round(args.delay / args.sampletime))
    delayed_temps = deque(maxlen=maxlen)
    delayed_temps.extend(maxlen * [args.kettle_temp])

    sim = Simulation(
        'autotune',
        PIDAutotune(
            args.setpoint, 100, args.sampletime, out_min=args.out_min,
            out_max=args.out_max, time=lambda: timestamp),
        Kettle(args.diameter, args.volume, args.kettle_temp),
        delayed_temps,
        [], [], [], []
    )

    # Run autotune until completed
    while not sim.sut.run(sim.delayed_temps[0]):
        timestamp += args.sampletime
        sim_update(sim, timestamp, sim.sut.output, args)
        if args.verbose > 0:
                print('time:    {0} sec'.format(timestamp))
                print('state: {0}'.format(sim.sut.state))
                print('{0}: {1:.2f}%'.format(sim.name, sim.sut.output))
                print('temp sensor:    {0:.2f}°C'.format(sim.sensor_temps[-1]))
                print('temp heater:    {0:.2f}°C'.format(sim.heater_temps[-1]))
                print()

    print('time:    {0} min'.format(round(timestamp / 60)))
    print('state:   {0}'.format(sim.sut.state))
    print()

    # On success, print params for each tuning rule
    if sim.sut.state == PIDAutotune.STATE_SUCCEEDED:
        for rule in sim.sut.tuning_rules:
            params = sim.sut.get_pid_parameters(rule)
            print('rule: {0}'.format(rule))
            print('Kp: {0}'.format(params.Kp))
            print('Ki: {0}'.format(params.Ki))
            print('Kd: {0}'.format(params.Kd))
            print()

    if args.export:
        write_csv(sim)

    if not args.noplot:
        title = 'PID autotune, {0:.1f}l kettle, {1:.1f}kW heater, {2:.1f}s delay'.format(
            args.volume, args.heater_power, args.delay)
        plot_simulations(args, [sim], title)


def simulate_pid(args):
    timestamp = 0  # seconds
    delayed_temps_len = max(1, round(args.delay / args.sampletime))
    sims = []

    # Create a simulation for each tuple pid(name, kp, ki, kd)
    for pid in args.pid:
        sim = Simulation(
            pid[0],
            PIDArduino(
                args.sampletime, float(pid[1]), float(pid[2]), float(pid[3]),
                args.out_min, args.out_max, lambda: timestamp),
            Kettle(args.diameter, args.volume, args.kettle_temp),
            deque(maxlen=delayed_temps_len),
            [], [], [], []
        )
        sims.append(sim)

    # Init delayed_temps deque for each simulation
    for sim in sims:
        sim.delayed_temps.extend(sim.delayed_temps.maxlen * [args.kettle_temp])

    # Run simulation for specified interval
    while timestamp < (args.interval * 60):
        timestamp += args.sampletime

        for sim in sims:
            output = sim.sut.calc(sim.delayed_temps[0], args.setpoint)
            output = max(output, 0)
            output = min(output, 100)
            sim_update(sim, timestamp, output, args)

            if args.verbose > 0 and not args.json_output:
                print('time:    {0} sec'.format(timestamp))
                print('{0}: {1:.2f}%'.format(sim.name, output))
                print('temp sensor:    {0:.2f}°C'.format(sim.sensor_temps[-1]))
                print('temp heater:    {0:.2f}°C'.format(sim.heater_temps[-1]))
        if args.verbose > 0 and not args.json_output:
            print()

    if args.export:
        for sim in sims:
            write_csv(sim)

    if not (args.noplot or args.json_output):
        title = 'PID simulation, {0:.1f}l kettle, {1:.1f}kW heater, {2:.1f}s delay'.format(
            args.volume, args.heater_power, args.delay)
        plot_simulations(args, sims, title)
    if args.json_output:
        return generate_result_by_sims(sims)


def run(cfg: Dict):
    args = Arg_nt(**cfg)

    if args.verbose > 1:
        logging.basicConfig(stream=sys.stderr, format=LOG_FORMAT, level=logging.DEBUG)
    if args.autotune:
        return simulate_autotune(args)
    if args.pid is not None:
        return simulate_pid(args)
