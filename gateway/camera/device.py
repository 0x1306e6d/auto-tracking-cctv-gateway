import logging

import numpy as np
import sys
import os
import random
import hashlib
import time

import cv2
import face_recognition
from scipy import*
from scipy.cluster import vq

from tornado import gen

from gateway import net
from gateway.camera.recognizor import recognize_face
from gateway.camera.tracker import track_object

top, bottom, left, right = 0, 1, 0, 1

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

        self.target_count = 1
        self.last_target_count = 1
        self.last_target_change_t = 0.0
        self.frame_count = 0
        self.last_frame_entity_list = []

        self.t0 = time.time()
        self.max_targets = 3

        self.display_image = None
        self.grey_image = None
        self.running_average_image = None
        self.running_average_in_display_color_depth = None
        self.difference = None

        self.face_image = face_recognition.load_image_file("./images/So-eun/01.jpg")
        self.face_encoding = face_recognition.face_encodings(self.face_image)[0]

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
        if self.__object_tracking_future:
            if self.__object_tracking_future.done():
                display_image = self.__object_tracking_future.result()

                self.__object_tracking_future = None

        if self.__face_recognition_future:
            if self.__face_recognition_future.done():
                names = self.__face_recognition_future.result()
                # logger.debug('Face recognization result: {}'.format(names))
                self.__face_recognition_future = None

        object_trackable = self.__object_tracking_future is None
        face_recognizable = self.__face_recognition_future is None
        if object_trackable or face_recognizable:
            frame = np.frombuffer(frame, np.uint8)
            frame = cv2.imdecode(frame, 1)

            if object_trackable:
                self.__object_tracking_future = self.__executor.submit(track_object, frame)
            if face_recognizable:
                self.__face_recognition_future = self.__executor.submit(recognize_face, frame, [self.face_encoding])

    def __recognize_face(self, frame):
        self.match_face(frame)
        return self.display_face_recognition(frame)

    def match_face(self, frame):
        if self.flag_face_recognition:
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

            self.face_locations = face_recognition.face_locations(small_frame)
            self.face_encodings = face_recognition.face_encodings(
                small_frame, self.face_locations)

            face_name = []
            for face_encoding in self.face_encodings:
                #match = face_recognition.compare_faces([self.face_encoding], face_encoding, 0.6)
                name = "Unknown"

                if match[0]:
                #name = "Seung tae"
                   name = "So eun"
                # self.flag_face_recognition

                self.face_names.append(name)

    def display_face_recognition(self, frame):
        display_image = frame
        for (top_, right_, bottom_, left_), name in zip(self.face_locations, self.face_names):
            top_ *= 4
            right_ *= 4
            bottom_ *= 4
            left_ *= 4

            cv2.rectangle(display_image, (left_, top_),
                          (right_, bottom_), (0, 0, 255), 2)
            #cv2.rectangle(display_image, (left_, bottom_ - 35), (right_, bottom_), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(display_image, name, (left_ + 6, bottom_ - 6),
                        font, 1.0, (255, 255, 255), 1)
        return display_image

    def merge_collided_bboxes(self, bbox_list):
        # For every bbox...
        for this_bbox in bbox_list:
            # Collision detect every other bbox:
            for other_bbox in bbox_list:
                if this_bbox is other_bbox:
                    continue  # Skip self

          # Assume a collision to start out with:
                has_collision = True

             # These coords are in screen coords, so > means
             # "lower than" and "further right than".  And <
             # means "higher than" and "further left than".

             # We also inflate the box size by 10% to deal with
             # fuzziness in the data.  (Without this, there are many times a bbox
             # is short of overlap by just one or two pixels.)
                if (this_bbox[bottom][0] * 1.1 < other_bbox[top][0] * 0.9):
                    has_collision = False
                if (this_bbox[top][0] * .9 > other_bbox[bottom][0] * 1.1):
                    has_collision = False
                if (this_bbox[right][1] * 1.1 < other_bbox[left][1] * 0.9):
                    has_collision = False
                if (this_bbox[left][1] * 0.9 > other_bbox[right][1] * 1.1):
                    has_collision = False

                if has_collision:
                    # merge these two bboxes into one, then start over:
                    top_left_x = min(this_bbox[left][0], other_bbox[left][0])
                    top_left_y = min(this_bbox[left][1], other_bbox[left][1])
                    bottom_right_x = max(
                        this_bbox[right][0], other_bbox[right][0])
                    bottom_right_y = max(
                        this_bbox[right][1], other_bbox[right][1])

                    new_bbox = ((top_left_x, top_left_y),
                                (bottom_right_x, bottom_right_y))

                    bbox_list.remove(this_bbox)
                    bbox_list.remove(other_bbox)
                    bbox_list.append(new_bbox)

                    # Start over with the new list:
                    return self.merge_collided_bboxes(bbox_list)
                    # When there are no collions between boxes, return that list:
        return bbox_list

    def getCenterpoint(self, frame):
        # Capture frame from webcam
        camera_image = frame

        self.frame_count += 1
        frame_t0 = time.time()

        if self.frame_count == 1:
            self.display_image = frame
            self.grey_image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            self.running_average_image = np.float32(frame)
            self.running_average_in_display_color_depth = self.display_image.copy()
            self.difference = self.display_image.copy()
            return self.display_image, 1

        # Create an image with interactive feedback:
        self.display_image = camera_image.copy()

        # Create a working "color image" to modify / blur
        color_image = self.display_image.copy()

        # Smooth to get rid of false positives
        color_image = cv2.GaussianBlur(color_image, (19, 19), 0)

        # Use the Running Average as the static background
        # a = 0.020 leaves artifacts lingering way too long.
        # a = 0.320 works well at 320x240, 15fps.  (1/a is roughly num frames.)
        cv2.accumulateWeighted(
            color_image, self.running_average_image, 0.320, None)

        # Convert the scale of the moving average.
        self.running_average_in_display_color_depth = cv2.convertScaleAbs(
            self.running_average_image)

        # Subtract the current frame from the moving average.
        cv2.absdiff(
            color_image, self.running_average_in_display_color_depth, self.difference)

        # Convert the image to greyscale.
        self.grey_image = cv2.cvtColor(self.difference, cv2.COLOR_BGR2GRAY)

        # Threshold the image to a black and white motion mask:
        ret, self.grey_image = cv2.threshold(
            self.grey_image, 2, 255, cv2.THRESH_BINARY)

        # Smooth and threshold again to eliminate "sparkles"
        self.grey_image = cv2.GaussianBlur(self.grey_image, (19, 19), 0)
        ret, self.grey_image = cv2.threshold(
            self.grey_image, 240, 255, cv2.THRESH_BINARY)
        non_black_coords_array = np.where(self.grey_image > 3)

        # Convert from numpy.where()'s two separate lists to one list of (x, y) tuples:
        non_black_coords_array = zip(
            non_black_coords_array[1], non_black_coords_array[0])

        # Was using this to hold either pixel coords or polygon coords.
        points = []
        bounding_box_list = []

        # Now calculate movements using the white pixels as "motion" data
        _, contour, hierarchy = cv2.findContours(
            self.grey_image, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contour:
            [x, y, w, h] = cv2.boundingRect(cnt)
            point1 = (x, y)
            point2 = (x + w, y + h)

            bounding_box_list.append((point1, point2))
            epsilon = 0.01 * cv2.arcLength(cnt, True)
            polygon_points = cv2.approxPolyDP(cnt, epsilon, True)

            # To track polygon points only (instead of every pixel):

        # Find the average size of the bbox (targets), then
        # remove any tiny bboxes (which are prolly just noise).
        # "Tiny" is defined as any box with 1/10th the area of the average box.
        # This reduces false positives on tiny "sparkles" noise.
        box_areas = []
        for box in bounding_box_list:
            box_width = box[right][0] - box[left][0]
            box_height = box[bottom][0] - box[top][0]
            box_areas.append(box_width * box_height)

        average_box_area = 0.0
        if len(box_areas):
            average_box_area = float(sum(box_areas)) / len(box_areas)

        trimmed_box_list = []
        for box in bounding_box_list:
            box_width = box[right][0] - box[left][0]
            box_height = box[bottom][0] - box[top][0]

            # Only keep the box if it's not a tiny noise box:
            if (box_width * box_height) > average_box_area * 0.1:
                trimmed_box_list.append(box)

        bounding_box_list = self.merge_collided_bboxes(trimmed_box_list)

        # Draw the merged box list:
        for box in bounding_box_list:
            cv2.rectangle(self.display_image, box[0], box[1], (0, 255, 0), 1)

        # Here are our estimate points to track, based on merged & trimmed boxes:
        estimated_target_count = len(bounding_box_list)

        # Don't allow target "jumps" from few to many or many to few.
        # Only change the number of targets up to one target per n seconds.
        # This fixes the "exploding number of targets" when something stops moving
        # and the motion erodes to disparate little puddles all over the place.

        if frame_t0 - self.last_target_change_t < .350:  # 1 change per 0.35 secs
            estimated_target_count = self.last_target_count
        else:
            if self.last_target_count - estimated_target_count > 1:
                estimated_target_count = self.last_target_count - 1
            if estimated_target_count - self.last_target_count > 1:
                estimated_target_count = self.last_target_count + 1
            self.last_target_change_t = frame_t0

        # Clip to the user-supplied maximum:
        estimated_target_count = min(estimated_target_count, self.max_targets)

        # The estimated_target_count at this point is the maximum number of targets
        # we want to look for.  If kmeans decides that one of our candidate
        # bboxes is not actually a target, we remove it from the target list below.

        # Using the numpy values directly (treating all pixels as points):
        #      points = grey_image
        points = non_black_coords_array
        center_points = []

        list(points)

        if len(list(points)):
            #      if len(bounding_box_list) :

            # If we have all the "target_count" targets from last frame,
            # use the previously known targets (for greater accuracy).

            criteria = (cv2.TERM_CRITERIA_EPS +
                        cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            flags = cv2.KMEANS_RANDOM_CENTERS

            compactness, labels, centers = cv2.kmeans(
                points, 2, None, criteria, 10, flags)

            for center_point in centers:
                #            print(center_point)
                center_points.append(center_point)

        # Now we have targets that are NOT computed from bboxes -- just
        # movement weights (according to kmeans).  If any two targets are
        # within the same "bbox count", average them into a single target.
        #
        # (Any kmeans targets not within a bbox are also kept.)
        trimmed_center_points = []
        removed_center_points = []

        for box in bounding_box_list:
            # Find the centers within this box:
            center_points_in_box = []

            for center_point in center_points:
                if center_point[0] < box[right][0] and center_point[0] > box[left][0] and \
                   center_point[1] < box[bottom][1] and center_point[1] > box[top][1]:

                      # This point is within the box.
                    center_points_in_box.append(center_point)

                # Now see if there are more than one.  If so, merge them.
            if len(center_points_in_box) > 1:
                # Merge them:
                x_list = y_list = []
                for point in center_points_in_box:
                    x_list.append(point[0])
                    y_list.append(point[1])

                average_x = int(float(sum(x_list)) / len(x_list))
                average_y = int(float(sum(y_list)) / len(y_list))

                trimmed_center_points.append((average_x, average_y))

                # Record that they were removed:
                removed_center_points += center_points_in_box

            if len(center_points_in_box) == 1:
                # Just use it.
                trimmed_center_points.append(center_points_in_box[0])

            # If there are any center_points not within a bbox, just use them.
            # (It's probably a cluster comprised of a bunch of small bboxes.)
        for center_point in center_points:
            if (not center_point in trimmed_center_points) and (not center_point in removed_center_points):
                trimmed_center_points.append(center_point)

        # Determine if there are any new (or lost) targets:
        actual_target_count = len(trimmed_center_points)
        self.last_target_count = actual_target_count

        # Now build the list of physical entities (objects)
        this_frame_entity_list = []

        # An entity is list: [ name, color, last_time_seen, last_known_coords ]

        for target in trimmed_center_points:

            # Is this a target near a prior entity (same physical entity)?
            entity_found = False
            entity_distance_dict = {}

            for entity in self.last_frame_entity_list:

                entity_coords = entity[3]
                delta_x = entity_coords[0] - target[0]
                delta_y = entity_coords[1] - target[1]

                distance = sqrt(pow(delta_x, 2) + pow(delta_y, 2))
                entity_distance_dict[distance] = entity

            # Did we find any non-claimed entities (nearest to furthest):
            distance_list = entity_distance_dict.keys()
            distance_list.sort()

            for distance in distance_list:

                # Yes; see if we can claim the nearest one:
                nearest_possible_entity = entity_distance_dict[distance]

                # Don't consider entities that are already claimed:
                if nearest_possible_entity in this_frame_entity_list:
                    # print "Target %s: Skipping the one iwth distance: %d at %s, C:%s" % (target, distance, nearest_possible_entity[3], nearest_possible_entity[1] )
                    continue

                # print "Target %s: USING the one iwth distance: %d at %s, C:%s" % (target, distance, nearest_possible_entity[3] , nearest_possible_entity[1])
                # Found the nearest entity to claim:
                entity_found = True
                nearest_possible_entity[2] = frame_t0  # Update last_time_seen
                nearest_possible_entity[3] = target  # Update the new location
                this_frame_entity_list.append(nearest_possible_entity)
                # log_file.write( "%.3f MOVED %s %d %d\n" % ( frame_t0, nearest_possible_entity[0], nearest_possible_entity[3][0], nearest_possible_entity[3][1]  ) )
                break

            if entity_found == False:
                # It's a new entity.
                color = (random.randint(0, 255), random.randint(
                    0, 255), random.randint(0, 255))
                name = hashlib.md5(str(frame_t0) + str(color)).hexdigest()[:6]
                last_time_seen = frame_t0

                new_entity = [name, color, last_time_seen, target]
                this_frame_entity_list.append(new_entity)
                # log_file.write( "%.3f FOUND %s %d %d\n" % ( frame_t0, new_entity[0], new_entity[3][0], new_entity[3][1]  ) )

        # Now "delete" any not-found entities which have expired:
        entity_ttl = 1.0  # 1 sec..

        for entity in self.last_frame_entity_list:
            last_time_seen = entity[2]
            if frame_t0 - last_time_seen > entity_ttl:
                # It's gone.
                # log_file.write( "%.3f STOPD %s %d %d\n" % ( frame_t0, entity[0], entity[3][0], entity[3][1]  ) )
                pass
            else:
                # Save it for next time... not expired yet:
                this_frame_entity_list.append(entity)

        # For next frame:
        self.last_frame_entity_list = this_frame_entity_list

        center_point = None

        for entity in bounding_box_list:
            if (int(entity[1][0] - entity[0][0]) > 50) & (int(entity[1][1] - entity[0][1]) > 50):
                center_point = int(
                    (entity[0][0] + entity[1][0]) / 2), int((entity[0][1] + entity[1][1]) / 2)
                cv2.circle(self.display_image,
                           center_point, 20, (0, 0, 255), 1)
                # cv2.circle(self.display_image, center_point, 15, (0,255,0), 1)
                cv2.circle(self.display_image,
                           center_point, 10, (255, 0, 0), 2)
                # cv2.circle(self.display_image, center_point,  5, (0,0,0), 3)

        # cv2.imshow("Motion",self.display_image)
        # cv2.waitKey(1)
        return self.display_image, center_point  # return center point
