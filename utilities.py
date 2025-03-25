import math


def line_segments_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
    """
    Check if two line segments intersect.
    """
    # Calculate directions
    d1x = x2 - x1
    d1y = y2 - y1
    d2x = x4 - x3
    d2y = y4 - y3

    # Calculate the determinant
    determinant = d1x * d2y - d1y * d2x

    # If determinant is very close to zero, lines are parallel
    if abs(determinant) < 1e-8:
        return False

    # Calculate parameters for the intersection point
    s = ((x1 - x3) * d2y - (y1 - y3) * d2x) / determinant
    t = ((x1 - x3) * d1y - (y1 - y3) * d1x) / determinant

    # Check if the intersection is within both line segments
    return 0 <= s <= 1 and 0 <= t <= 1


def point_in_rectangle(x, y, rect_x1, rect_y1, rect_x2, rect_y2):
    """Check if a point is inside a rectangle."""
    return (rect_x1 <= x <= rect_x2 and rect_y1 <= y <= rect_y2)


def line_intersects_rectangle(line_x1, line_y1, line_x2, line_y2, rect_x1, rect_y1, rect_x2, rect_y2):
    """
    Check if a line intersects with a rectangle.
    """
    # Check if either endpoint is inside the rectangle
    if point_in_rectangle(line_x1, line_y1, rect_x1, rect_y1, rect_x2, rect_y2) or \
            point_in_rectangle(line_x2, line_y2, rect_x1, rect_y1, rect_x2, rect_y2):
        return True

    # Check if line intersects with any of the four edges of the rectangle
    rect_edges = [
        (rect_x1, rect_y1, rect_x2, rect_y1),  # Top edge
        (rect_x1, rect_y2, rect_x2, rect_y2),  # Bottom edge
        (rect_x1, rect_y1, rect_x1, rect_y2),  # Left edge
        (rect_x2, rect_y1, rect_x2, rect_y2)  # Right edge
    ]

    for edge_x1, edge_y1, edge_x2, edge_y2 in rect_edges:
        if line_segments_intersect(
                line_x1, line_y1, line_x2, line_y2,
                edge_x1, edge_y1, edge_x2, edge_y2
        ):
            return True

    return False


def has_line_of_sight(start_pos, end_pos, walls):
    """
    Check if there's a line of sight between start_pos and end_pos.

    Args:
        start_pos: Tuple (x, y) of the starting position
        end_pos: Tuple (x, y) of the ending position
        walls: List of wall coordinates (x_min, y_min, x_max, y_max)

    Returns:
        True if there's a clear line of sight, False if a wall blocks the view
    """
    start_x, start_y = start_pos
    end_x, end_y = end_pos

    # Check each wall for intersection
    for wall in walls:
        if line_intersects_rectangle(
                start_x, start_y, end_x, end_y,
                wall[0], wall[1], wall[2], wall[3]
        ):
            return False  # Wall blocks line of sight

    # No walls block the view
    return True


def distance_squared(pos1, pos2):
    """Calculate squared distance between two positions"""
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    return dx * dx + dy * dy


def cast_ray(start_pos, angle, max_distance, walls):
    """
    Cast a ray from start_pos in the given angle direction until it hits a wall or reaches max_distance.

    Args:
        start_pos: Tuple (x, y) of the starting position
        angle: Angle in radians for the ray direction
        max_distance: Maximum distance for the ray
        walls: List of wall coordinates (x_min, y_min, x_max, y_max)

    Returns:
        Tuple (x, y) of the endpoint of the ray
    """
    # Calculate the ray direction vector
    dx = math.cos(angle)
    dy = math.sin(angle)

    # Calculate the ray end point if it doesn't hit anything
    end_x = start_pos[0] + dx * max_distance
    end_y = start_pos[1] + dy * max_distance

    # Initialize the closest intersection point to the max distance
    closest_intersection = (end_x, end_y)
    closest_dist_squared = max_distance * max_distance

    # Check intersection with each wall
    for wall in walls:
        wall_x1, wall_y1, wall_x2, wall_y2 = wall

        # Check all four edges of the wall
        edges = [
            (wall_x1, wall_y1, wall_x2, wall_y1),  # Top edge
            (wall_x1, wall_y2, wall_x2, wall_y2),  # Bottom edge
            (wall_x1, wall_y1, wall_x1, wall_y2),  # Left edge
            (wall_x2, wall_y1, wall_x2, wall_y2)  # Right edge
        ]

        for edge_x1, edge_y1, edge_x2, edge_y2 in edges:
            # Calculate intersection using the line-line intersection formula
            intersection = line_line_intersection(
                start_pos[0], start_pos[1], end_x, end_y,
                edge_x1, edge_y1, edge_x2, edge_y2
            )

            if intersection:
                # Calculate distance to intersection (squared)
                ix, iy = intersection
                dist_squared = (ix - start_pos[0]) ** 2 + (iy - start_pos[1]) ** 2

                # Keep the closest intersection
                if dist_squared < closest_dist_squared:
                    closest_intersection = intersection
                    closest_dist_squared = dist_squared

    return closest_intersection


def line_line_intersection(x1, y1, x2, y2, x3, y3, x4, y4):
    """
    Calculate the intersection point of two line segments if it exists.

    Args:
        x1, y1: First point of first line segment
        x2, y2: Second point of first line segment
        x3, y3: First point of second line segment
        x4, y4: Second point of second line segment

    Returns:
        Tuple (x, y) of intersection point, or None if no intersection
    """
    # Calculate determinant
    den = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)

    # If lines are parallel, no intersection
    if abs(den) < 1e-8:
        return None

    # Calculate line parameters
    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / den
    ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / den

    # If intersection is within both line segments
    if 0 <= ua <= 1 and 0 <= ub <= 1:
        # Calculate intersection point
        x = x1 + ua * (x2 - x1)
        y = y1 + ua * (y2 - y1)
        return (x, y)

    return None
