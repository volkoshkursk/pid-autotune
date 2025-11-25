#!/bin/python3

from pid_autotune import run
import sys
import argparse

def parser_add_args(parser):
    parser.add_argument(
        '-p', '--pid', dest='pid', nargs=4, metavar=('name', 'kp', 'ki', 'kd'),
        default=None, action='append', help='simulate a PID controller')
    parser.add_argument(
        '-a', '--atune', dest='autotune', default=False,
        action='store_true', help='simulate autotune')

    parser.add_argument(
        '-v', '--verbose', dest='verbose', default=0,
        action='count', help='be verbose')
    parser.add_argument(
        '-e', '--export', dest='export', default=False,
        action='store_true', help='export data to a .csv file')
    parser.add_argument(
        '-n', '--noplot', dest='noplot', default=False,
        action='store_true', help='do not plot the results')

    parser.add_argument(
        '-t', '--temp', dest='kettle_temp', metavar='T', default=40.0,
        type=float, help='initial kettle temperature in °C (default: 40)')
    parser.add_argument(
        '-s', '--setpoint', dest='setpoint', metavar='T', default=45.0,
        type=float, help='target temperature in °C (default: 45)')
    parser.add_argument(
        '--ambient', dest='ambient_temp', metavar='T', default=20.0,
        type=float, help='ambient temperature in °C (default: 20)')

    parser.add_argument(
        '-i', '--interval', dest='interval', metavar='t', default=20,
        type=int, help='simulated interval in minutes (default: 20)')
    parser.add_argument(
        '-d', '--delay', dest='delay', metavar='t', default=15.0,
        type=float, help='system response delay in seconds (default: 15)')
    parser.add_argument(
        '--sampletime', dest='sampletime', metavar='t', default=5.0,
        type=float, help='temperature sample time in seconds (default: 5)')

    parser.add_argument(
        '--volume', dest='volume', metavar='V', default=70.0,
        type=float, help='kettle content volume in liters (default: 70)')
    parser.add_argument(
        '--diameter', dest='diameter', metavar='d', default=50.0,
        type=float, help='kettle diameter in cm (default: 50)')

    parser.add_argument(
        '--power', dest='heater_power', metavar='P', default=6.0,
        type=float, help='heater power in kW (default: 6)')
    parser.add_argument(
        '--heatloss', dest='heat_loss_factor', metavar='x', default=1.0,
        type=float, help='kettle heat loss factor (default: 1)')

    parser.add_argument(
        '--minout', dest='out_min', metavar='x', default=0.0,
        type=float, help='minimum PID controller output (default: 0)')
    parser.add_argument(
        '--maxout', dest='out_max', metavar='x', default=100.0,
        type=float, help='maximum PID controller output (default: 100)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser_add_args(parser)

    if len(sys.argv) == 1:
        parser.print_help()
    else:
        run(vars(parser.parse_args()))
        
