import logging

from tornado import gen

from gateway import net

logger = logging.getLogger(__name__)


class CameraDevice(object):
    def __init__(self, stream, address):
        self.resolution = None
        self.framerate = None
        self.__stream = stream
        self.__address = address
        self.__subscribors = {}

    @gen.coroutine
    def send(self, opcode, body=None):
        packet = net.encode_packet(opcode, body)
        yield self.__stream.write(packet)

    @gen.coroutine
    def broadcast(self, packet):
        for k in self.__subscribors:
            subscribor = self.__subscribors[k]
            logger.debug('Broadcasting {} bytes to {}'.format(len(packet), k))
            yield subscribor.write(packet)

    def subscribe(self, stream):
        logger.debug('Subscribe stream {}'.format(stream))
        self.__subscribors[id(stream)] = stream

    def unsubscribe(self, stream):
        logger.debug('Unsubscribe stream {}'.format(stream))
        del self.__subscribors[id(stream)]
