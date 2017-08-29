from tornado import gen

from gateway import net


class CameraDevice(object):
    def __init__(self, stream, address):
        self.resolution = None
        self.framerate = None
        self.__stream = stream
        self.__address = address

    @gen.coroutine
    def send(self, opcode, body=None):
        packet = net.encode_packet(opcode, body)
        yield self.__stream.write(packet)
