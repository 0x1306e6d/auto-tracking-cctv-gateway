import base64
import logging
import struct
import threading

from tornado import gen
from tornado.iostream import StreamClosedError
from tornado.tcpserver import TCPServer

from gateway import net
from gateway.camera.device import CameraDevice

logger = logging.getLogger(__name__)


class CameraTCPServer(TCPServer):

    __instance_lock = threading.Lock()
    __instance = None

    @staticmethod
    def instance():
        if not CameraTCPServer.__instance:
            with CameraTCPServer.__instance_lock:
                if not CameraTCPServer.__instance:
                    CameraTCPServer.__instance = CameraTCPServer()
        return CameraTCPServer.__instance

    def __init__(self):
        super(CameraTCPServer, self).__init__()
        self.__camera_group = {}
        self.__camera_id_generator = 0

    def get_camera(self, camera_id):
        return self.__camera_group[camera_id]

    def handle_setup(self, camera, body):
        body = struct.unpack('!IIH', body)
        resolution = (body[0], body[1])
        framerate = body[2]
        logger.info('Setup camera device. resolution: {}, framerate: {}'.
                    format(resolution, framerate))

        camera.resolution = resolution
        camera.framerate = framerate
        camera.send(net.Opcode.RECORD)

        self.__camera_group[self.__camera_id_generator] = camera
        self.__camera_id_generator += 1

    def handle_frame(self, camera, body):
        frame = base64.b64encode(body)
        frame += b'\n'

        camera.broadcast(frame)

    @gen.coroutine
    def handle_stream(self, stream, address):
        logger.info('New camera stream from {}'.format(address))

        camera = CameraDevice(stream, address)
        while True:
            try:
                packet_size = struct.calcsize('!L')
                packet_size = yield stream.read_bytes(packet_size)
                packet_size = struct.unpack('!L', packet_size)[0]

                packet = yield stream.read_bytes(packet_size)
                opcode, body = net.decode_packet(packet)

                if opcode == net.Opcode.SETUP:
                    self.handle_setup(camera, body)
                elif opcode == net.Opcode.FRAME:
                    self.handle_frame(camera, body)
                else:
                    logger.error('Invalid packet opcode: {}, body: {}'.
                                 format(opcode, packet))

            except StreamClosedError:
                logger.info('Camera stream is closed.')
                break
