import logging
import logging.config
import os.path

from gateway.config import (
    LOGGING_FILE_NAME,
)


def load_logging_settings(logging_file_name=LOGGING_FILE_NAME):
    logging.debug('Loading logging settings from %s', os.path.realpath(logging_file_name))
    logging.config.fileConfig(logging_file_name)
