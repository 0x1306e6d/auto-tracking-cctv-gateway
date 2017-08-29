import logging

from tornado.ioloop import IOLoop

from gateway.conf import (
    CAMERA_NETWORK_IP,
    CAMERA_NETWORK_TCP_PORT,
)
from gateway.camera.tcp import CameraTCPServer

logger = logging.getLogger(__name__)


def main():
    CameraTCPServer.instance().listen(
        CAMERA_NETWORK_TCP_PORT, address=CAMERA_NETWORK_IP)

    IOLoop.instance().start()


if __name__ == '__main__':
    main()
