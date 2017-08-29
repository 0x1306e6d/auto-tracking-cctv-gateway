import logging
import os

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

from gateway.conf import (
    CAMERA_NETWORK_IP,
    CAMERA_NETWORK_TCP_PORT,
    MOBILE_NETWORK_IP,
    MOBILE_NETWORK_HTTP_PORT,
    MOBILE_NETWORK_TCP_PORT,
)
from gateway.camera.tcp import CameraTCPServer
from gateway.mobile.http import get_application
from gateway.mobile.tcp import MobileTCPServer

logger = logging.getLogger(__name__)


def configure_logger():
    fmt = '[%(asctime)s][%(threadName)s:%(module)s:%(funcName)s [%(lineno)d]]'
    fmt += os.linesep
    fmt += '[%(levelname)7s] %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=fmt)


def main():
    configure_logger()

    CameraTCPServer.instance().listen(
        CAMERA_NETWORK_TCP_PORT, address=CAMERA_NETWORK_IP)

    HTTPServer(get_application()).listen(
        MOBILE_NETWORK_HTTP_PORT, address=MOBILE_NETWORK_IP)

    MobileTCPServer.instance().listen(
        MOBILE_NETWORK_TCP_PORT, address=MOBILE_NETWORK_IP)

    IOLoop.instance().start()


if __name__ == '__main__':
    main()
