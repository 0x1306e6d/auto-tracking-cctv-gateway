import logging

from tornado import gen

from gateway import net

logger = logging.getLogger(__name__)


class CameraDevice(object):
    def __init__(self, stream, address):
        self.__stream = stream
        self.address = address
        self.resolution = None
        self.framerate = None

    @gen.coroutine
    def send(self, opcode, body=None):
        packet = net.encode_packet(opcode, body)
        yield self.__stream.write(packet)
