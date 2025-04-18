import json
import numpy as np
import pygame


BLACK = [0, 0, 0]
WHITE = [255, 255, 255]
GREEN = [0, 255, 0]
RED = [255, 0, 0]

def load_grid_from_json(file_path):
    """
    Load a grid representing the environment layout from a JSON file.

    Args:
        file_path (str): The path to the JSON file containing the grid data.

    Returns:
        list: A 2D list representing the grid, or None if loading fails.
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Grid file not found at {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return None

def convert_grid_to_elements(grid, scale_factor=1.0):
    """
    Convert a grid of RGB color values into lists of pygame Rects for walls, exits, and doors.

    Args:
        grid (list): A 2D list where each cell contains an RGB color list [R, G, B].
        scale_factor (float, optional): A factor to scale the coordinates and dimensions
                                        of the resulting Rects. Defaults to 1.0.

    Returns:
        tuple: A tuple containing three lists: (list_of_wall_rects, list_of_exit_rects, list_of_door_rects).
               Rects are pygame.Rect objects. Returns ([], [], []) if the input grid is None.
    """
    if grid is None:
        return [], [], []

    height = len(grid)
    width = len(grid[0])
    walls = []
    exits = []
    doors = []

    for y in range(height):
        for x in range(width):
            cell_color = grid[y][x]
            if not isinstance(cell_color, (list, tuple)) or len(cell_color) != 3:
                 continue

            rect = pygame.Rect(
                int(x * scale_factor),
                int(y * scale_factor),
                int(scale_factor + 0.5),
                int(scale_factor + 0.5)
            )

            if cell_color == BLACK:
                walls.append(rect)
            elif cell_color == GREEN:
                exits.append(rect)
            elif cell_color == RED:
                doors.append(rect)

    return walls, exits, doors


def integrate_grid_into_simulation(grid_file, simulation_width, simulation_height):
    """
    Load a grid file, convert its elements, and scale them to fit simulation dimensions.

    Args:
        grid_file (str): Path to the grid.json file.
        simulation_width (int): The target width of the simulation area.
        simulation_height (int): The target height of the simulation area.

    Returns:
        tuple: A tuple containing three lists: (list_of_wall_rects, list_of_exit_rects, list_of_door_rects).
               Returns ([], [], []) if grid loading or processing fails.
    """
    grid = load_grid_from_json(grid_file)
    if grid is None:
        print("Warning: Failed to load grid. Returning empty elements.")
        return [], [], []

    grid_height = len(grid)
    grid_width = len(grid[0])
    if grid_height == 0 or grid_width == 0:
        print("Warning: Loaded grid has zero dimensions. Returning empty elements.")
        return [], [], []

    scale_x = simulation_width / grid_width
    scale_y = simulation_height / grid_height
    avg_scale = (scale_x + scale_y) / 2.0

    walls, exits, doors = convert_grid_to_elements(grid, avg_scale)

    print(f"Loaded {len(walls)} wall rects, {len(exits)} exit rects, and {len(doors)} door rects from grid.")
    return walls, exits, doors