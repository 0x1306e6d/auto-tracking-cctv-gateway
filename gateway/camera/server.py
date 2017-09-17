import base64
import logging
import multiprocessing
import struct

from concurrent.futures import ProcessPoolExecutor

from tornado import gen
from tornado.iostream import StreamClosedError
from tornado.tcpserver import TCPServer

from gateway import net
from gateway.conf import (
    CAMERA_NETWORK_IP,
    CAMERA_NETWORK_TCP_PORT,
)
from gateway.camera.device import CameraDevice


def handle_setup(server, camera, packet):
    packet = struct.unpack('!IIH', packet)
    resolution = (packet[0], packet[1])
    framerate = packet[2]
    logging.info('Setup camera device. resolution: {}, framerate: {}'.
                 format(resolution, framerate))

    camera.resolution = resolution
    camera.framerate = framerate
    camera.send(net.Opcode.RECORD)

    server.add_camera(camera)


def handle_frame(server, camera, packet):
    frame = packet
    camera.try_image_processing(frame)

    encoded_frame = base64.b64encode(packet)
    encoded_frame += b'\n'
    camera.broadcast_to_watchers(encoded_frame)


class CameraTCPServer(TCPServer):
    def __init__(self, parent):
        super(CameraTCPServer, self).__init__()
        self.__parent = parent
        self.__handlers = {}
        self.__handlers[net.Opcode.SETUP] = handle_setup
        self.__handlers[net.Opcode.FRAME] = handle_frame

    @gen.coroutine
    def handle_stream(self, stream, address):
        logging.info('New camera stream from {}'.format(address))

        camera = CameraDevice(stream, address, self.__parent.executor)

        while True:
            try:
                packet_size = struct.calcsize('!L')
                packet_size = yield stream.read_bytes(packet_size)
                packet_size = struct.unpack('!L', packet_size)[0]

                packet = yield stream.read_bytes(packet_size)
                opcode, body = net.decode_packet(packet)

                # logging.debug('[PACKET] opcode: {}, body: {}'.format(opcode, len(body)))

                handler = self.__handlers.get(opcode)
                if handler:
                    handler(self.__parent, camera, body)
                else:
                    logging.error('Invalid packet opcode: {}, body: {}'.
                                  format(opcode, packet))
                    break
            except StreamClosedError:
                break

        logging.info('Camera stream is closed.')
        self.__parent.remove_camera(camera)


class CameraServer(object):
    def __init__(self):
        self.executor = ProcessPoolExecutor(multiprocessing.cpu_count())
        self.__cameras = {}
        self.__tcp_server = CameraTCPServer(self)

    def add_camera(self, camera):
        self.__cameras[id(camera)] = camera

    def remove_camera(self, camera):
        if self.__cameras.get(id(camera)) is not None:
            del self.__cameras[id(camera)]

    def cameras(self):
        for k in self.__cameras.keys():
            yield self.__cameras.get(k)

    def camera(self, camera_id):
        return self.__cameras.get(camera_id)

    def listen(self, port=CAMERA_NETWORK_TCP_PORT, address=CAMERA_NETWORK_IP):
        self.__tcp_server.listen(port, address=address)
        logging.info('Listening camera tcp server on {}:{}'.
                     format(address, port))
