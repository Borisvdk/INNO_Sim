import math


def line_segments_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
    """
    Check if two finite line segments intersect.

    Args:
        x1, y1: Coordinates of the first point of the first segment.
        x2, y2: Coordinates of the second point of the first segment.
        x3, y3: Coordinates of the first point of the second segment.
        x4, y4: Coordinates of the second point of the second segment.

    Returns:
        bool: True if the segments intersect, False otherwise.
    """
    d1x = x2 - x1
    d1y = y2 - y1
    d2x = x4 - x3
    d2y = y4 - y3

    determinant = d1x * d2y - d1y * d2x

    if abs(determinant) < 1e-8:
        return False

    s = ((x1 - x3) * d2y - (y1 - y3) * d2x) / determinant
    t = ((x1 - x3) * d1y - (y1 - y3) * d1x) / determinant

    return 0 <= s <= 1 and 0 <= t <= 1


def point_in_rectangle(x, y, rect_x1, rect_y1, rect_x2, rect_y2):
    """
    Check if a point (x, y) lies within a rectangle defined by its corners.

    Args:
        x, y: Coordinates of the point.
        rect_x1, rect_y1: Coordinates of the top-left corner of the rectangle.
        rect_x2, rect_y2: Coordinates of the bottom-right corner of the rectangle.

    Returns:
        bool: True if the point is inside the rectangle (inclusive), False otherwise.
    """
    return (rect_x1 <= x <= rect_x2 and rect_y1 <= y <= rect_y2)


def line_intersects_rectangle(line_x1, line_y1, line_x2, line_y2, wall_rect):
    """
    Check if a line segment intersects with a pygame.Rect object.

    Args:
        line_x1, line_y1: Coordinates of the first point of the line segment.
        line_x2, line_y2: Coordinates of the second point of the line segment.
        wall_rect (pygame.Rect): The rectangle object to check against.

    Returns:
        bool: True if the line segment intersects the rectangle, False otherwise.
    """
    try:
        clipped_line = wall_rect.clipline(line_x1, line_y1, line_x2, line_y2)
        return bool(clipped_line)
    except TypeError:
        print(f"Warning: TypeError in clipline with line ({line_x1},{line_y1})-({line_x2},{line_y2}) and rect {wall_rect}")
        return False


def has_line_of_sight(start_pos, end_pos, obstacles):
    """
    Check if there is an unobstructed line of sight between two points, considering obstacles.

    Args:
        start_pos (tuple): The starting (x, y) coordinates.
        end_pos (tuple): The ending (x, y) coordinates.
        obstacles (list): A list of pygame.Rect objects representing vision-blocking elements.

    Returns:
        bool: True if there is a clear line of sight, False if an obstacle intersects the line segment.
    """
    start_x, start_y = start_pos
    end_x, end_y = end_pos

    for obstacle_rect in obstacles:
        if line_intersects_rectangle(
            start_x, start_y, end_x, end_y,
            obstacle_rect
        ):
            return False

    return True


def distance_squared(pos1, pos2):
    """
    Calculate the squared Euclidean distance between two points.
    Useful for comparisons where the exact distance is not needed, avoiding sqrt.

    Args:
        pos1 (tuple): The first point (x, y).
        pos2 (tuple): The second point (x, y).

    Returns:
        float: The squared distance between pos1 and pos2.
    """
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    return dx * dx + dy * dy


def cast_ray(start_pos, angle, max_distance, obstacles):
    """
    Cast a ray from a starting point in a given direction and find the first intersection point with obstacles.

    Args:
        start_pos (tuple): The (x, y) origin of the ray.
        angle (float): The angle of the ray in radians.
        max_distance (float): The maximum distance the ray should travel if no obstacle is hit.
        obstacles (list): A list of pygame.Rect objects representing potential obstacles.

    Returns:
        tuple: The (x, y) coordinates of the intersection point, or the point at max_distance
               along the angle if no intersection occurs within that distance.
    """
    start_x, start_y = start_pos
    dx = math.cos(angle)
    dy = math.sin(angle)
    ray_end_x = start_x + dx * max_distance
    ray_end_y = start_y + dy * max_distance

    closest_intersection = (ray_end_x, ray_end_y)
    min_dist_sq = max_distance * max_distance

    for obstacle_rect in obstacles:
        edges = [
            (obstacle_rect.topleft, obstacle_rect.topright),
            (obstacle_rect.bottomleft, obstacle_rect.bottomright),
            (obstacle_rect.topleft, obstacle_rect.bottomleft),
            (obstacle_rect.topright, obstacle_rect.bottomright)
        ]
        for p1, p2 in edges:
            edge_x1, edge_y1 = p1
            edge_x2, edge_y2 = p2
            intersection = line_line_intersection(
                start_x, start_y, ray_end_x, ray_end_y,
                edge_x1, edge_y1, edge_x2, edge_y2
            )
            if intersection:
                dist_sq = distance_squared(start_pos, intersection)
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    closest_intersection = intersection

    return closest_intersection


def line_line_intersection(x1, y1, x2, y2, x3, y3, x4, y4):
    """
    Calculate the intersection point of two line segments if it exists within both segments.

    Args:
        x1, y1: Coordinates of the first point of the first line segment.
        x2, y2: Coordinates of the second point of the first line segment.
        x3, y3: Coordinates of the first point of the second line segment.
        x4, y4: Coordinates of the second point of the second line segment.

    Returns:
        tuple: The (x, y) coordinates of the intersection point if it lies on both segments,
               or None otherwise.
    """
    den = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)

    if abs(den) < 1e-8:
        return None

    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / den
    ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / den

    if 0 <= ua <= 1 and 0 <= ub <= 1:
        x = x1 + ua * (x2 - x1)
        y = y1 + ua * (y2 - y1)
        return (x, y)

    return None