import json
import logging
import struct

from flask import Flask, request

from tornado import gen
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError
from tornado.tcpserver import TCPServer
from tornado.wsgi import WSGIContainer

from gateway.app import gateway
from gateway.conf import (
    MOBILE_NETWORK_IP,
    MOBILE_NETWORK_HTTP_PORT,
    MOBILE_NETWORK_TCP_PORT,
)
from gateway.firebase import fcm

flask = Flask(__name__)


@flask.route('/cameras', methods=['GET'])
def handle_camera_list_request():
    cameras = gateway.camera_server.cameras()

    if not cameras:
        return json.dumps({
            'success': False,
            'reason': 'cameras are not initialized.'
        })
    else:
        return json.dumps([camera.to_dict() for camera in cameras])


@flask.route('/camera/<int:camera_id>', methods=['GET'])
def handle_camera_request(camera_id):
    camera = gateway.camera_server.camera(camera_id)

    if not camera:
        return json.dumps({
            'success': False,
            'reason': 'camera {} is not exist.'.format(camera_id)
        })
    else:
        return json.dumps(camera.to_dict())


@flask.route('/camera/<int:camera_id>/move', methods=['POST'])
def handle_camera_move_request(camera_id):
    body = request.data.decode('utf-8')
    body = json.loads(body)
    direction = body['direction']

    camera = gateway.camera_server.camera(camera_id)
    if not camera:
        return json.dumps({
            'success': False,
            'reason': 'camera {} is not exist.'.format(camera_id)
        })
    else:
        camera.move(direction)
        return json.dumps({
            'success': True
        })


@flask.route('/token', methods=['POST'])
def handle_update_token():
    body = request.data.decode('utf-8')
    body = json.loads(body)

    if 'token' in body:
        token = body['token']
        logging.debug('Received firebase token: %s', token)

        fcm.insert_token(token)

        return json.dumps({
            'success': True
        })


class MobileTCPServer(TCPServer):
    def __init__(self, parent):
        super(MobileTCPServer, self).__init__()
        self.__parent = parent

    @gen.coroutine
    def handle_stream(self, stream, address):
        logging.info('New mobile stream {} from {}'.format(stream, address))

        camera_id = None

        def on_close(data):
            logging.info('Close mobile stream {}'.format(stream))

            camera = gateway.camera_server.camera(camera_id)
            if camera is not None:
                camera.unsubscribe(stream)

        def on_data(data):
            logging.info('Read camera id from mobile stream {}'.format(stream))

            camera_id = int(struct.unpack('!Q', data)[0])
            camera = gateway.camera_server.camera(camera_id)
            if camera is not None:
                camera.subscribe(stream)
                stream.read_until_close(on_close)

        stream.read_bytes(struct.calcsize('!Q'), on_data)


class MobileServer(object):
    def __init__(self):
        self.__http_server = HTTPServer(WSGIContainer(flask))
        self.__tcp_server = MobileTCPServer(self)

    def listen(self,
               http_port=MOBILE_NETWORK_HTTP_PORT,
               tcp_port=MOBILE_NETWORK_TCP_PORT,
               address=MOBILE_NETWORK_IP):
        self.__http_server.listen(http_port, address=address)
        logging.info('Listening mobile http server on {}:{}'.
                     format(address, http_port))

        self.__tcp_server.listen(tcp_port, address=address)
        logging.info('Listening mobile tcp server on {}:{}'.
                     format(address, tcp_port))
