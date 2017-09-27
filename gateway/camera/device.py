import cv2
import face_recognition as fr
import logging
import numpy as np
import struct
import time

from tornado import gen

from gateway import net, face
from gateway.app import gateway
from gateway.camera.recognizor import recognize_face
from gateway.camera.tracker import track_object
from gateway.firebase import fcm

MOVE_TOP = 0x01
MOVE_BOTTOM = 0x02
MOVE_LEFT = 0x04
MOVE_RIGHT = 0x08


class CameraDevice(object):
    def __init__(self, stream, address, executor):
        self.__stream = stream
        self.address = address
        self.resolution = None
        self.framerate = None
        self.moving = False
        self.__watchers = {}
        self.__executor = executor
        self.__object_tracking_future = None
        self.__face_recognition_future = None

        # For object tracking
        self.__running_average_image = None
        self.__running_average_in_display_color_depth = None
        self.__difference = None
        self.__last_target_count = None
        self.__last_target_change_time = None
        self.__last_frame_entity_list = None

        self._last_notified_faces = {}

    def to_dict(self):
        return {
            'id': id(self),
            'address': {
                'ip': self.address[0],
                'port': self.address[1]
            },
            'resolution': {
                'width': self.resolution[0],
                'height': self.resolution[1]
            },
            'framerate': self.framerate
        }

    @gen.coroutine
    def send(self, opcode, body=None):
        packet = net.encode_packet(opcode, body)
        yield self.__stream.write(packet)

    @gen.coroutine
    def broadcast_to_watchers(self, packet):
        for k in self.__watchers.keys():
            stream = self.__watchers.get(k)
            if not stream.closed():
                yield stream.write(packet)

    def subscribe(self, stream):
        if id(stream) not in self.__watchers:
            self.__watchers[id(stream)] = stream

    def unsubscribe(self, stream):
        if id(stream) in self.__watchers:
            del self.__watchers[id(stream)]

    def move(self, direction):
        if not self.moving:
            self.moving = True

            body = struct.pack('!H', direction)
            self.send(net.Opcode.MOVE_REQUEST, body)

    def try_image_processing(self, frame):
        self.__fetch_object_tracking_result()
        self._fetch_face_recognition_result()

        is_object_trackable = self.__object_tracking_future is None
        is_face_recognizable = self.__face_recognition_future is None
        if is_object_trackable or is_face_recognizable:
            frame = np.frombuffer(frame, np.uint8)
            frame = cv2.imdecode(frame, 1)

            if is_object_trackable:
                self.__execute_object_tracking(frame)

            if is_face_recognizable:
                self._execute_face_recognition(frame)

    def __fetch_object_tracking_result(self):
        if self.__object_tracking_future:
            if self.__object_tracking_future.done():
                point, \
                    running_average_image, \
                    running_average_in_display_color_depth, \
                    difference, \
                    last_target_count, \
                    last_target_change_time, \
                    last_frame_entity_list = self.__object_tracking_future.result()

                self.__running_average_image = running_average_image
                self.__running_average_in_display_color_depth = running_average_in_display_color_depth
                self.__difference = difference
                self.__last_target_count = last_target_count
                self.__last_target_change_time = last_target_change_time
                self.__last_frame_entity_list = last_frame_entity_list

                if point is not None:
                    logging.debug('Object tracking result: {}'.format(point))

                self.__object_tracking_future = None

    def __execute_object_tracking(self, frame):
        self.__object_tracking_future = self.__executor.submit(track_object,
                                                               frame,
                                                               self.__running_average_image,
                                                               self.__running_average_in_display_color_depth,
                                                               self.__difference,
                                                               self.__last_target_count,
                                                               self.__last_target_change_time,
                                                               self.__last_frame_entity_list)

    def _handle_face_recognition_result(self, faces):
        now = time.time()
        to_notify_names = []

        for name, distance in faces:
            if name in self._last_notified_faces:
                if (now - self._last_notified_faces[name]) > 60:
                    to_notify_names.append(name)
            else:
                to_notify_names.append(name)

        if len(to_notify_names) > 0:
            if 'Uhknown' in to_notify_names:
                message_title = "Warning"
                message_body = "Unknown people are detected"
            else:
                message_title = "People are detected"
                message_body = to_notify_names
            result = fcm.notify_all(message_title, message_body)
            if result:
                logging.debug('Notify result: {}'.format(result))

            for name in filter(lambda x: x is not 'Unknown', to_notify_names):
                if name in self._last_notified_faces:
                    del self._last_notified_faces[name]
                self._last_notified_faces[name] = now

    def _fetch_face_recognition_result(self):
        if self.__face_recognition_future:
            if self.__face_recognition_future.done():
                faces = self.__face_recognition_future.result()
                if len(faces) > 0:
                    logging.debug('Face recognition result: %s', faces)
                    self._handle_face_recognition_result(faces)

                self.__face_recognition_future = None

    def _execute_face_recognition(self, frame):
        self.__face_recognition_future = self.__executor.submit(
            face.recognize_face, frame, gateway.faces)
