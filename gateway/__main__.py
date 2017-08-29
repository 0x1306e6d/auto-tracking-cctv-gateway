import logging
import os

from tornado.ioloop import IOLoop

from gateway.conf import (
    CAMERA_NETWORK_IP,
    CAMERA_NETWORK_TCP_PORT,
)
from gateway.camera.tcp import CameraTCPServer

logger = logging.getLogger(__name__)


def configure_logger():
    fmt = '[%(asctime)s][%(threadName)s:%(module)s:%(funcName)s [%(lineno)d]]'
    fmt += os.linesep
    fmt += '[%(levelname)5s] %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=fmt)


def main():
    configure_logger()

    CameraTCPServer.instance().listen(
        CAMERA_NETWORK_TCP_PORT, address=CAMERA_NETWORK_IP)

    IOLoop.instance().start()


if __name__ == '__main__':
    main()
