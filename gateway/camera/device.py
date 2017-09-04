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
        self.__watchers = {}

    @gen.coroutine
    def send(self, opcode, body=None):
        packet = net.encode_packet(opcode, body)
        yield self.__stream.write(packet)

    @gen.coroutine
    def broadcast_to_watchers(self, packet):
        for k in self.__watchers.keys():
            stream = self.__watchers.get(k)
            if not stream.closed():
                stream.write(packet)

    def subscribe(self, stream):
        if id(stream) not in self.__watchers:
            self.__watchers[id(stream)] = stream

    def unsubscribe(self, stream):
        if id(stream) in self.__watchers:
            del self.__watchers[id(stream)]
