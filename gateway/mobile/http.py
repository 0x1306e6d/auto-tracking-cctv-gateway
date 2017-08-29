import logging
import threading

from tornado.httpserver import HTTPServer
from tornado.web import Application, RequestHandler

logger = logging.getLogger(__name__)


class CameraRequestHandler(RequestHandler):
    # TODO: Handle camera requests
    pass


class MoveRequestHandler(RequestHandler):
    def post(self):
        # TODO: Move camera
        pass


class ModeRequestHandler(RequestHandler):
    def post(self):
        # TODO: Select mode
        pass


def get_application():
    return Application([
        (r'/camera', CameraRequestHandler),
        (r'/move', MoveRequestHandler),
        (r'/mode', ModeRequestHandler),
    ])
