import logging
import struct

from flask import Flask

from tornado import gen
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError
from tornado.tcpserver import TCPServer
from tornado.wsgi import WSGIContainer

from gateway.conf import (
    MOBILE_NETWORK_IP,
    MOBILE_NETWORK_HTTP_PORT,
    MOBILE_NETWORK_TCP_PORT,
)

logger = logging.getLogger(__name__)
flask = Flask(__name__)


@flask.route('/camera/<int:camera_id>', methods=['GET'])
def handle_camera_request(camera_id):
    return 'handle_camera_{}_request'.format(camera_id)


@flask.route('/cameras', methods=['GET'])
def handle_camera_list_request():
    return 'handle_camera_list_request'


class MobileTCPServer(TCPServer):
    def __init__(self, parent):
        super(MobileTCPServer, self).__init__()
        self.__parent = parent

    @gen.coroutine
    def handle_stream(self, stream, address):
        logger.info('New mobile stream {} from {}'.format(stream, address))

        while True:
            try:
                packet_size = struct.calcsize('!L')
                packet = yield stream.read_bytes(packet_size)
                packet = struct.unpack('!L', packet)[0]

            except StreamClosedError:
                break

        logger.info('Mobile stream {} is closed.'.format(stream))


class MobileServer(object):
    def __init__(self):
        self.__http_server = HTTPServer(WSGIContainer(flask))
        self.__tcp_server = MobileTCPServer(self)

    def listen(self,
               http_port=MOBILE_NETWORK_HTTP_PORT,
               tcp_port=MOBILE_NETWORK_TCP_PORT,
               address=MOBILE_NETWORK_IP):
        self.__http_server.listen(http_port, address=address)
        logger.info('Listening mobile http server on {}:{}'.
                    format(address, http_port))

        self.__tcp_server.listen(tcp_port, address=address)
        logger.info('Listening mobile tcp server on {}:{}'.
                    format(address, tcp_port))
