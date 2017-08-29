import logging
import threading

from tornado import gen
from tornado.iostream import StreamClosedError
from tornado.tcpserver import TCPServer

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
                # TODO: handle camera's stream
                pass
            except StreamClosedError:
                logger.info('Camera stream is closed.')
                break
