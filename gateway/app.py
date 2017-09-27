import logging
import os.path

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

from gateway import face
from gateway.conf import (
    CAMERA_NETWORK_IP,
    CAMERA_NETWORK_TCP_PORT,
    MOBILE_NETWORK_IP,
    MOBILE_NETWORK_HTTP_PORT,
    MOBILE_NETWORK_TCP_PORT,
)
from gateway.util import paths

gateway = None


def start(args):
    global gateway
    gateway = Gateway(args)
    gateway.start()


class Gateway(object):
    def __init__(self, args):
        self.__args = args
        self.camera_server = None
        self.mobile_server = None
        self.faces = []

    def _load_faces(self):
        logging.debug('Loading faces...')

        for face_name in paths.children_names('faces'):
            logging.debug("Loading %s's faces...", face_name)

            face_encodings = []
            for face_image_path in paths.children('faces', face_name):
                if face_image_path.suffix in ['.jpg', '.png']:
                    logging.debug("Loading %s's face from %s", face_name, face_image_path)
                    face_image = face.load_face_image(face_image_path)
                    face_encoding = face.encode_face(face_image)
                    face_encodings.append(face_encoding)

            if len(face_encodings) > 0:
                logging.info("%s's %d faces are loaded.", face_name, len(face_encodings))
                self.faces.append(face.Face(face_name, face_encodings))

        logging.info('All faces are loaded.')

    def start(self):
        logging.info('Starting auto tracking cctv gateway')
        logging.debug('args = {}'.format(self.__args))

        self._load_faces()
        self.__init_camera_server()
        self.__init_mobile_server()

        IOLoop.instance().start()

    def __init_camera_server(self):
        from gateway.camera.server import CameraServer

        self.camera_server = CameraServer()
        self.camera_server.listen()
        logging.info('Camera server is initialized.')

    def __init_mobile_server(self):
        from gateway.mobile.server import MobileServer

        self.mobile_server = MobileServer()
        self.mobile_server.listen()
        logging.info('Mobile server is initialized.')
