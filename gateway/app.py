import logging

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

from gateway.conf import (
    CAMERA_NETWORK_IP,
    CAMERA_NETWORK_TCP_PORT,
    MOBILE_NETWORK_IP,
    MOBILE_NETWORK_HTTP_PORT,
    MOBILE_NETWORK_TCP_PORT,
)
from gateway.camera.server import CameraServer
from gateway.mobile.http import get_application
from gateway.mobile.tcp import MobileTCPServer

logger = logging.getLogger(__name__)


class Gateway(object):
    def __init__(self, args):
        self.__args = args
        self.camera_server = None

    def start(self):
        logging.info('Starting auto tracking cctv gateway')
        logging.debug('args = {}'.format(self.__args))

        self.__init_camera_server()

        HTTPServer(get_application()).listen(
            MOBILE_NETWORK_HTTP_PORT, address=MOBILE_NETWORK_IP)
        logger.info('Mobile HTTP server is started.')

        MobileTCPServer.instance().listen(
            MOBILE_NETWORK_TCP_PORT, address=MOBILE_NETWORK_IP)
        logger.info('Mobile TCP server is started.')

        IOLoop.instance().start()

    def __init_camera_server(self):
        self.camera_server = CameraServer()
        self.camera_server.listen()
        logger.info('Camera server is initialized.')
