import argparse
import logging
import os

from gateway.app import start


def configure_logging():
    format = '[%(asctime)s][%(threadName)s:%(module)s:%(funcName)s [%(lineno)d]]'
    format += os.linesep
    format += '[%(levelname)7s] %(message)s'

    logging.basicConfig(format=format, level=logging.DEBUG)
    logging.debug('logging is configured.')


def parse_args():
    parser = argparse.ArgumentParser(description='Auto Tracking CCTV Gateway')

    return parser.parse_args()


def start_from_command_line():
    configure_logging()
    start(parse_args())
