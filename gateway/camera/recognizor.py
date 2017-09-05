import cv2
import face_recognition


def recognize_face(frame, faces, tolerance=0.50):
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

    locations = face_recognition.face_locations(small_frame)
    encodings = face_recognition.face_encodings(small_frame, locations)

    names = []
    for encoding in encodings:
        matchs = face_recognition.compare_faces(faces, encoding, tolerance)
        if matchs[0]:
            names.append('So eun')
        else:
            names.append('Unknown')

    __display_face_recognization(frame, locations, names)

    return names

def __display_face_recognization(frame, locations, names):
    for (top, right, bottom, left), name in zip(locations, names):
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
    cv2.imshow('face_recognition', frame)
    cv2.waitKey(1)
