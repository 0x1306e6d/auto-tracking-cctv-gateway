import cv2
import face_recognition as fr
import logging
import numpy as np

from tornado import gen

from gateway import net
from gateway.camera.recognizor import recognize_face
from gateway.camera.tracker import track_object

logger = logging.getLogger(__name__)


class CameraDevice(object):
    def __init__(self, stream, address, executor):
        self.__stream = stream
        self.address = address
        self.resolution = None
        self.framerate = None
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

        # For face recognization
        self.__faces_to_recognize = fr.face_encodings(
            fr.load_image_file("./images/So-eun/01.jpg"))[0]

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

    def try_image_processing(self, frame):
        self.__fetch_object_tracking_result()
        self.__fetch_face_recognization_result()

        is_object_trackable = self.__object_tracking_future is None
        is_face_recognizable = self.__face_recognition_future is None
        if is_object_trackable or is_face_recognizable:
            frame = np.frombuffer(frame, np.uint8)
            frame = cv2.imdecode(frame, 1)

            if is_object_trackable:
                self.__execute_object_tracking(frame)

            if is_face_recognizable:
                self.__execute_face_recognization(frame)

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
                    logger.debug('Object tracking result: {}'.format(point))

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

    def __fetch_face_recognization_result(self):
        if self.__face_recognition_future:
            if self.__face_recognition_future.done():
                names = self.__face_recognition_future.result()

                if names and len(names) > 0:
                    logger.debug('Face recognization result: {}'.format(names))

                self.__face_recognition_future = None

    def __execute_face_recognization(self, frame):
        self.__face_recognition_future = self.__executor.submit(recognize_face,
                                                                frame,
                                                                [self.__faces_to_recognize])
