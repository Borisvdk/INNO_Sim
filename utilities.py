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


def line_intersects_rectangle(line_x1, line_y1, line_x2, line_y2, wall_rect):
    """
    Check if a line intersects with a pygame.Rect wall.
    Uses pygame.Rect.clipline internally.
    """
    try:
        # clipline returns the clipped line segment within the rect if it intersects,
        # or an empty tuple () if it doesn't.
        clipped_line = wall_rect.clipline(line_x1, line_y1, line_x2, line_y2)
        return bool(clipped_line) # True if clipline didn't return empty tuple
    except TypeError:
        # Handle potential errors if coordinates are not numbers
        print(f"Warning: TypeError in clipline with line ({line_x1},{line_y1})-({line_x2},{line_y2}) and rect {wall_rect}")
        return False


def has_line_of_sight(start_pos, end_pos, wall_rects):
    """
    Check if there's a line of sight between start_pos and end_pos, avoiding wall Rects.

    Args:
        start_pos: Tuple (x, y) of the starting position
        end_pos: Tuple (x, y) of the ending position
        wall_rects: List of pygame.Rect objects representing walls.

    Returns:
        True if there's a clear line of sight, False if a wall blocks the view
    """
    start_x, start_y = start_pos
    end_x, end_y = end_pos

    # Check each wall rectangle for intersection
    for wall_rect in wall_rects:
        if line_intersects_rectangle(
            start_x, start_y, end_x, end_y,
            wall_rect # Pass the pygame.Rect directly
        ):
            return False # Wall blocks line of sight

    # No walls block the view
    return True


def distance_squared(pos1, pos2):
    """Calculate squared distance between two positions"""
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    return dx * dx + dy * dy


def cast_ray(start_pos, angle, max_distance, wall_rects):
    """
    Cast a ray from start_pos, checking intersections with wall Rects.

    Args:
        start_pos: Tuple (x, y)
        angle: Angle in radians
        max_distance: Maximum distance
        wall_rects: List of pygame.Rect objects for walls

    Returns:
        Tuple (x, y) of the endpoint (either max_distance or collision point)
    """
    start_x, start_y = start_pos
    dx = math.cos(angle)
    dy = math.sin(angle)

    # Calculate potential end point
    ray_end_x = start_x + dx * max_distance
    ray_end_y = start_y + dy * max_distance

    closest_intersection = (ray_end_x, ray_end_y)
    min_dist_sq = max_distance * max_distance

    for wall_rect in wall_rects:
        # Define the 4 edges of the rectangle
        edges = [
            (wall_rect.topleft, wall_rect.topright),
            (wall_rect.bottomleft, wall_rect.bottomright),
            (wall_rect.topleft, wall_rect.bottomleft),
            (wall_rect.topright, wall_rect.bottomright)
        ]

        for p1, p2 in edges:
            edge_x1, edge_y1 = p1
            edge_x2, edge_y2 = p2

            intersection = line_line_intersection(
                start_x, start_y, ray_end_x, ray_end_y, # The full potential ray
                edge_x1, edge_y1, edge_x2, edge_y2      # The wall edge
            )

            if intersection:
                ix, iy = intersection
                dist_sq = distance_squared(start_pos, intersection)

                # If this intersection is closer than the current minimum
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    closest_intersection = intersection

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
