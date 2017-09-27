import logging

from itertools import repeat

import cv2
import face_recognition as fr

from gateway.config import (
    DISPLAY_RECOGNIZED_FACES,
)


def load_face_image(face_image_path):
    return fr.load_image_file(face_image_path)


def encode_face(face_image):
    return fr.face_encodings(face_image)[0]


class Face(object):
    def __init__(self, name, encodings):
        self.name = name
        self.encodings = encodings


def _display_recognized_faces(image, faces):
    for (name, distance), (top, right, bottom, left) in faces:
        cv2.rectangle(image, (left, top), (right, bottom), (0, 0, 255), 2)

        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(image, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
    cv2.imshow('display', image)
    cv2.waitKey(1)


def recognize_face(image, known_faces, tolerance=0.50):
    face_locations = fr.face_locations(image)
    face_encodings = fr.face_encodings(image, face_locations)

    faces = list(repeat(('Unknown', 1.0), len(face_encodings)))
    for index, face_encoding in enumerate(face_encodings):
        face = faces[index]
        for known_face in known_faces:
            distances = fr.face_distance(known_face.encodings, face_encoding)
            min_distance = min(distances)
            if min_distance < face[1] and min_distance < tolerance:
                face = (known_face.name, min_distance)
        faces[index] = face

    if DISPLAY_RECOGNIZED_FACES:
        _display_recognized_faces(image, list(zip(faces, face_locations)))

    return faces
