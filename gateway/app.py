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

gateway = None


def start(args):
    global gateway
    gateway = Gateway(args)
    gateway.start()


class Gateway(object):
    def __init__(self, args):
        self.__args = args
        self.camera_server = None
        self.mobile_server = None

    def start(self):
        logging.info('Starting auto tracking cctv gateway')
        logging.debug('args = {}'.format(self.__args))

        self.__init_camera_server()
        self.__init_mobile_server()

        IOLoop.instance().start()

    def __init_camera_server(self):
        from gateway.camera.server import CameraServer

        self.camera_server = CameraServer()
        self.camera_server.listen()
        logging.info('Camera server is initialized.')

    def __init_mobile_server(self):
        from gateway.mobile.server import MobileServer

        self.mobile_server = MobileServer()
        self.mobile_server.listen()
        logging.info('Mobile server is initialized.')
