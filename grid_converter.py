import json
import numpy as np
import pygame # <-- Import pygame here

# Define colors used in the grid file
BLACK = [0, 0, 0]
WHITE = [255, 255, 255]
GREEN = [0, 255, 0] # <-- Define Green for exits
RED = [255, 0, 0] 

def load_grid_from_json(file_path):
    """Load a grid from a JSON file."""
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
    Convert a grid of RGB values to wall, exit, and door definitions.

    Args:
        grid: 3D list/array where colors define element types.
        scale_factor: Factor to scale coordinates by.

    Returns:
        Tuple: (list_of_wall_rects, list_of_exit_rects, list_of_door_rects)
               Rects are pygame.Rect objects.
    """
    if grid is None:
        return [], [], [] # Return three empty lists

    height = len(grid)
    width = len(grid[0])
    walls = []
    exits = []
    doors = [] # <-- Add list for doors

    for y in range(height):
        for x in range(width):
            cell_color = grid[y][x]
            # Ensure cell_color is a list/tuple of 3 integers
            if not isinstance(cell_color, (list, tuple)) or len(cell_color) != 3:
                 # print(f"Warning: Invalid cell format at ({x},{y}): {cell_color}. Skipping.")
                 continue # Skip malformed cells silently or log warning

            # Convert color list to tuple for direct comparison if necessary
            # Although direct list comparison usually works
            # cell_color_tuple = tuple(cell_color)

            rect = pygame.Rect(
                int(x * scale_factor),
                int(y * scale_factor),
                int(scale_factor + 0.5), # Add 0.5 before int() for better rounding
                int(scale_factor + 0.5)
            )

            # Compare with list literals directly
            if cell_color == BLACK:
                walls.append(rect)
            elif cell_color == GREEN:
                exits.append(rect)
            elif cell_color == RED: # <-- Check for doors
                doors.append(rect)

    return walls, exits, doors # <-- Return doors


def integrate_grid_into_simulation(grid_file, simulation_width, simulation_height):
    """
    Load a grid file and convert it to walls, exits, and doors for the simulation.

    Args:
        grid_file: Path to the grid.json file
        simulation_width: Width of the simulation area
        simulation_height: Height of the simulation area

    Returns:
        Tuple: (list_of_wall_rects, list_of_exit_rects, list_of_door_rects)
               Returns ([], [], []) if grid loading fails.
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

    # Convert grid to walls, exits, and doors
    walls, exits, doors = convert_grid_to_elements(grid, avg_scale)

    print(f"Loaded {len(walls)} wall rects, {len(exits)} exit rects, and {len(doors)} door rects from grid.")
    return walls, exits, doors # <-- Return all three lists