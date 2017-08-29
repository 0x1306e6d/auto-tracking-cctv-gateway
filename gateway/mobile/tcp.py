import logging
import threading

from tornado import gen
from tornado.iostream import StreamClosedError
from tornado.tcpserver import TCPServer

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

        while True:
            try:
                # TODO: Handle mobile's stream
                pass
            except StreamClosedError:
                logger.info('Mobile stream is closed.')
                break
