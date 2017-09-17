import argparse
import logging
import os

from gateway.app import start
from gateway.util import utils


def parse_args():
    parser = argparse.ArgumentParser(description='Auto Tracking CCTV Gateway')

    return parser.parse_args()


def start_from_command_line():
    utils.load_logging_settings()
    logging.info('Logging is configured.')

    start(parse_args())
