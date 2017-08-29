import logging
import struct
import threading

from tornado import gen
from tornado.iostream import StreamClosedError
from tornado.tcpserver import TCPServer

from gateway.camera.tcp import CameraTCPServer

logger = logging.getLogger(__name__)


class MobileTCPServer(TCPServer):

    __instance_lock = threading.Lock()
    __instance = None

    @staticmethod
    def instance():
        if not MobileTCPServer.__instance:
            with MobileTCPServer.__instance_lock:
                if not MobileTCPServer.__instance:
                    MobileTCPServer.__instance = MobileTCPServer()
        return MobileTCPServer.__instance

    def __init__(self):
        super(MobileTCPServer, self).__init__()

    @gen.coroutine
    def handle_stream(self, stream, address):
        logger.info('New mobile stream from {}'.format(address))

        camera_id = -1
        while True:
            try:
                packet_size = struct.calcsize('!L')
                packet = yield stream.read_bytes(packet_size)
                packet = struct.unpack('!L', packet)[0]

                camera_id = int(packet)
                camera = CameraTCPServer.instance().get_camera(camera_id)
                if camera:
                    camera.subscribe(stream)
                else:
                    stream.close()
            except StreamClosedError:
                logger.info('Mobile stream is closed.')
                break

        if not camera_id == -1:
            camera = CameraTCPServer.instance().get_camera(camera_id)
            if camera:
                camera.unsubscribe(stream)
