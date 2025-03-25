import json
import numpy as np


def load_grid_from_json(file_path):
    """Load a grid from a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def convert_grid_to_walls(grid, scale_factor=1.0):
    """
    Convert a grid of RGB values to wall definitions.

    Args:
        grid: 3D array where [0, 0, 0] represents walls and [255, 255, 255] represents empty space
        scale_factor: Factor to scale coordinates by (useful for matching simulation dimensions)

    Returns:
        List of wall tuples in the format (x1, y1, x2, y2)
    """
    # Convert grid to a 2D array where 1 represents walls, 0 represents empty space
    height = len(grid)
    width = len(grid[0])
    binary_grid = np.zeros((height, width), dtype=int)

    for y in range(height):
        for x in range(width):
            # Check if the pixel is black (wall)
            if grid[y][x] == [0, 0, 0]:
                binary_grid[y, x] = 1

    # Find horizontal wall segments
    horizontal_walls = []
    for y in range(height):
        start_x = None
        for x in range(width):
            # Start of a wall segment
            if binary_grid[y, x] == 1 and start_x is None:
                start_x = x
            # End of a wall segment
            elif binary_grid[y, x] == 0 and start_x is not None:
                # Only add if the segment is at least 2 pixels wide
                if x - start_x >= 2:
                    # Format: (x1, y1, x2, y2)
                    horizontal_walls.append((
                        int(start_x * scale_factor),
                        int(y * scale_factor),
                        int(x * scale_factor),
                        int((y + 1) * scale_factor)
                    ))
                start_x = None
        # Check for wall segments that end at grid boundary
        if start_x is not None:
            # Only add if the segment is at least 2 pixels wide
            if width - start_x >= 2:
                horizontal_walls.append((
                    int(start_x * scale_factor),
                    int(y * scale_factor),
                    int(width * scale_factor),
                    int((y + 1) * scale_factor)
                ))

    # Find vertical wall segments
    vertical_walls = []
    for x in range(width):
        start_y = None
        for y in range(height):
            # Start of a wall segment
            if binary_grid[y, x] == 1 and start_y is None:
                start_y = y
            # End of a wall segment
            elif binary_grid[y, x] == 0 and start_y is not None:
                # Only add if the segment is at least 2 pixels high
                if y - start_y >= 2:
                    # Format: (x1, y1, x2, y2)
                    vertical_walls.append((
                        int(x * scale_factor),
                        int(start_y * scale_factor),
                        int((x + 1) * scale_factor),
                        int(y * scale_factor)
                    ))
                start_y = None
        # Check for wall segments that end at grid boundary
        if start_y is not None:
            # Only add if the segment is at least 2 pixels high
            if height - start_y >= 2:
                vertical_walls.append((
                    int(x * scale_factor),
                    int(start_y * scale_factor),
                    int((x + 1) * scale_factor),
                    int(height * scale_factor)
                ))

    # Combine all walls
    walls = horizontal_walls + vertical_walls
    return walls


def integrate_grid_into_simulation(grid_file, simulation_width, simulation_height):
    """
    Load a grid file and convert it to walls for the simulation.

    Args:
        grid_file: Path to the grid.json file
        simulation_width: Width of the simulation area
        simulation_height: Height of the simulation area

    Returns:
        List of wall tuples in the format (x1, y1, x2, y2)
    """
    # Load the grid
    grid = load_grid_from_json(grid_file)

    # Calculate scale factors to match simulation dimensions
    grid_height = len(grid)
    grid_width = len(grid[0])
    scale_x = simulation_width / grid_width
    scale_y = simulation_height / grid_height
    scale_factor = min(scale_x, scale_y)  # Use the smaller scale to ensure walls fit in simulation

    # Convert grid to walls
    walls = convert_grid_to_walls(grid, scale_factor)

    return walls