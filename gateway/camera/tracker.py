import cv2
import time
import numpy as np

MAX_TARGETS = 3

TOP = 0
BOTTOM = 1
LEFT = 0
RIGHT = 1


def __init_tracker(frame):
    running_average_image = np.float32(frame)
    running_average_in_display_color_depth = frame.copy()
    difference = frame.copy()
    last_target_count = 1
    last_target_change_time = 0.0
    last_frame_entity_list = []

    return None, \
        running_average_image, \
        running_average_in_display_color_depth, \
        difference, \
        last_target_count, \
        last_target_change_time, \
        last_frame_entity_list


def __merge_collided_bboxes(bbox_list):
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
            if (this_bbox[BOTTOM][0] * 1.1 < other_bbox[TOP][0] * 0.9):
                has_collision = False
            if (this_bbox[TOP][0] * .9 > other_bbox[BOTTOM][0] * 1.1):
                has_collision = False
            if (this_bbox[RIGHT][1] * 1.1 < other_bbox[LEFT][1] * 0.9):
                has_collision = False
            if (this_bbox[LEFT][1] * 0.9 > other_bbox[RIGHT][1] * 1.1):
                has_collision = False

            if has_collision:
                # merge these two bboxes into one, then start over:
                top_left_x = min(this_bbox[LEFT][0], other_bbox[LEFT][0])
                top_left_y = min(this_bbox[LEFT][1], other_bbox[LEFT][1])
                bottom_right_x = max(this_bbox[RIGHT][0], other_bbox[RIGHT][0])
                bottom_right_y = max(this_bbox[RIGHT][1], other_bbox[RIGHT][1])

                new_bbox = ((top_left_x, top_left_y),
                            (bottom_right_x, bottom_right_y))

                bbox_list.remove(this_bbox)
                bbox_list.remove(other_bbox)
                bbox_list.append(new_bbox)

                # Start over with the new list:
                return __merge_collided_bboxes(bbox_list)
                # When there are no collions between boxes, return that list:
    return bbox_list


def __display_tracked_objects(frame):
    cv2.imshow('display', frame)
    cv2.waitKey(1)


def track_object(frame,
                 running_average_image,
                 running_average_in_display_color_depth,
                 difference,
                 last_target_count,
                 last_target_change_time,
                 last_frame_entity_list):

    if difference is None:
        return __init_tracker(frame)

    frame_time = time.time()

    # Create a working "color image" to modify / blur
    color_image = frame.copy()
    # Smooth to get rid of false positives
    color_image = cv2.GaussianBlur(color_image, (19, 19), 0)

    # Use the Running Average as the static background
    # a = 0.020 leaves artifacts lingering way too long.
    # a = 0.320 works well at 320x240, 15fps.  (1/a is roughly num frames.)
    cv2.accumulateWeighted(color_image, running_average_image, 0.320, None)

    # Convert the scale of the moving average.
    running_average_in_display_color_depth = cv2.convertScaleAbs(
        running_average_image)

    # Subtract the current frame from the moving average.
    cv2.absdiff(color_image, running_average_in_display_color_depth, difference)

    # Convert the image to greyscale.
    grey_image = cv2.cvtColor(difference, cv2.COLOR_BGR2GRAY)

    # Threshold the image to a black and white motion mask:
    _, grey_image = cv2.threshold(grey_image, 2, 255, cv2.THRESH_BINARY)

    # Smooth and threshold again to eliminate "sparkles"
    grey_image = cv2.GaussianBlur(grey_image, (19, 19), 0)
    _, grey_image = cv2.threshold(grey_image, 240, 255, cv2.THRESH_BINARY)
    non_black_coords_array = np.where(grey_image > 3)

    # Convert from numpy.where()'s two separate lists to one list of (x, y) tuples:
    non_black_coords_array = zip(
        non_black_coords_array[1], non_black_coords_array[0])

    # Was using this to hold either pixel coords or polygon coords.
    points = []
    bounding_box_list = []

    # Now calculate movements using the white pixels as "motion" data
    _, contour, hierarchy = cv2.findContours(
        grey_image, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

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
        box_width = box[RIGHT][0] - box[LEFT][0]
        box_height = box[BOTTOM][0] - box[TOP][0]
        box_areas.append(box_width * box_height)

    average_box_area = 0.0
    if len(box_areas):
        average_box_area = float(sum(box_areas)) / len(box_areas)
    trimmed_box_list = []

    for box in bounding_box_list:
        box_width = box[RIGHT][0] - box[LEFT][0]
        box_height = box[BOTTOM][0] - box[TOP][0]

        # Only keep the box if it's not a tiny noise box:
        if (box_width * box_height) > average_box_area * 0.1:
            trimmed_box_list.append(box)

    bounding_box_list = __merge_collided_bboxes(trimmed_box_list)

    # Draw the merged box list:
    for box in bounding_box_list:
        cv2.rectangle(frame, box[0], box[1], (0, 255, 0), 1)

    # Here are our estimate points to track, based on merged & trimmed boxes:
    estimated_target_count = len(bounding_box_list)

    # Don't allow target "jumps" from few to many or many to few.
    # Only change the number of targets up to one target per n seconds.
    # This fixes the "exploding number of targets" when something stops moving
    # and the motion erodes to disparate little puddles all over the place.

    # 1 change per 0.35 secs
    if (frame_time - last_target_change_time) < .350:
        estimated_target_count = last_target_count
    else:
        if (last_target_count - estimated_target_count) > 1:
            estimated_target_count = last_target_count - 1
        if (estimated_target_count - last_target_count) > 1:
            estimated_target_count = last_target_count + 1
        last_target_change_time = frame_time

    # Clip to the user-supplied maximum:
    estimated_target_count = min(estimated_target_count, MAX_TARGETS)

    # The estimated_target_count at this point is the maximum number of targets
    # we want to look for.  If kmeans decides that one of our candidate
    # bboxes is not actually a target, we remove it from the target list below.

    # Using the numpy values directly (treating all pixels as points):
    points = non_black_coords_array
    center_points = []

    list(points)
    if len(list(points)):
        # If we have all the "target_count" targets from last frame,
        # use the previously known targets (for greater accuracy).
        criteria = (cv2.TERM_CRITERIA_EPS +
                    cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        flags = cv2.KMEANS_RANDOM_CENTERS
        compactness, labels, centers = cv2.kmeans(
            points, 2, None, criteria, 10, flags)
        for center_point in centers:
            center_points.append(center_point)

    # Now we have targets that are NOT computed from bboxes -- just
    # movement weights (according to kmeans).  If any two targets are
    # within the same "bbox count", average them into a single target.
    # (Any kmeans targets not within a bbox are also kept.)
    trimmed_center_points = []
    removed_center_points = []

    for box in bounding_box_list:
        # Find the centers within this box:
        center_points_in_box = []

        for center_point in center_points:
            if center_point[0] < box[RIGHT][0] and \
                    center_point[0] > box[LEFT][0] and \
                    center_point[1] < box[BOTTOM][1] and \
                    center_point[1] > box[TOP][1]:
                # This point is within the box.
                center_points_in_box.append(center_point)

            # Now see if there are more than one.  If so, merge them.
            if len(center_points_in_box) > 1:
                # Merge them:
                x_list = []
                y_list = []
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
        if (not center_point in trimmed_center_points) and \
                (not center_point in removed_center_points):
            trimmed_center_points.append(center_point)

    # Determine if there are any new (or lost) targets:
    actual_target_count = len(trimmed_center_points)
    last_target_count = actual_target_count

    # Now build the list of physical entities (objects)
    this_frame_entity_list = []

    # An entity is list: [name, color, last_time_seen, last_known_coords]
    for target in trimmed_center_points:
        # Is this a target near a prior entity (same physical entity)?
        entity_found = False
        entity_distance_dict = {}

        for entity in last_frame_entity_list:
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
                continue

            # Found the nearest entity to claim:
            entity_found = True
            # Update last_time_seen
            nearest_possible_entity[2] = frame_time
            # Update the new location
            nearest_possible_entity[3] = target
            this_frame_entity_list.append(nearest_possible_entity)
            break

        if not entity_found:
            # It's a new entity.
            color = (random.randint(0, 255), random.randint(
                0, 255), random.randint(0, 255))
            name = hashlib.md5(str(frame_time) + str(color)).hexdigest()[:6]
            last_time_seen = frame_time

            new_entity = [name, color, last_time_seen, target]
            this_frame_entity_list.append(new_entity)

    # Now "delete" any not-found entities which have expired:
    entity_ttl = 1.0  # 1 sec

    for entity in last_frame_entity_list:
        last_time_seen = entity[2]
        if frame_time - last_time_seen > entity_ttl:
            # It's gone.
            pass
        else:
            # Save it for next time... not expired yet:
            this_frame_entity_list.append(entity)

    # For next frame:
    last_frame_entity_list = this_frame_entity_list

    center_point = None

    for entity in bounding_box_list:
        if (int(entity[1][0] - entity[0][0]) > 50) & (int(entity[1][1] - entity[0][1]) > 50):
            center_point = int(
                (entity[0][0] + entity[1][0]) / 2), int((entity[0][1] + entity[1][1]) / 2)
            cv2.circle(frame, center_point, 20, (0, 0, 255), 1)
            cv2.circle(frame, center_point, 10, (255, 0, 0), 2)

    __display_tracked_objects(frame)

    return center_point, \
        running_average_image, \
        running_average_in_display_color_depth, \
        difference, \
        last_target_count, \
        last_target_change_time, \
        last_frame_entity_list
