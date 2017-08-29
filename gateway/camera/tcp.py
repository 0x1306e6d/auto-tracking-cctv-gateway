import logging
import threading

from tornado import gen
from tornado.iostream import StreamClosedError
from tornado.tcpserver import TCPServer

from gateway import net

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

    @gen.coroutine
    def handle_stream(self, stream, address):
        logger.info('New camera stream from {}'.format(address))

        while True:
            try:
                packet_size = struct.calcsize('!L')
                packet_size = yield stream.read_bytes(packet_size)
                packet_size = struct.unpack('!L', packet_size)[0]

                packet = yield stream.read_bytes(packet_size)
                opcode, body = net.decode_packet(packet)

                if opcode == net.Opcode.SETUP:
                    pass
                else:
                    logger.error('Invalid packet opcode: {}, body: {}'.
                                 format(opcode, packet))

            except StreamClosedError:
                logger.info('Camera stream is closed.')
                break
