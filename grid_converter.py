import json
import numpy as np
import pygame # <-- Import pygame here

# Define colors used in the grid file
BLACK = [0, 0, 0]
WHITE = [255, 255, 255]
GREEN = [0, 255, 0] # <-- Define Green for exits

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
    Convert a grid of RGB values to wall and exit definitions.

    Args:
        grid: 3D list/array where colors define element types.
        scale_factor: Factor to scale coordinates by.

    Returns:
        Tuple: (list_of_wall_rects, list_of_exit_rects)
               Rects are pygame.Rect objects.
    """
    if grid is None:
        return [], []

    height = len(grid)
    width = len(grid[0])
    walls = []
    exits = []

    # We'll create simple Rects for each wall/exit cell first
    # More complex merging could be added later if needed for performance
    for y in range(height):
        for x in range(width):
            cell_color = grid[y][x]
            rect = pygame.Rect(
                int(x * scale_factor),
                int(y * scale_factor),
                int(scale_factor), # Keep width/height as scaled cell size
                int(scale_factor)
            )

            if cell_color == BLACK:
                walls.append(rect)
            elif cell_color == GREEN:
                exits.append(rect)

    return walls, exits


def integrate_grid_into_simulation(grid_file, simulation_width, simulation_height):
    """
    Load a grid file and convert it to walls and exits for the simulation.

    Args:
        grid_file: Path to the grid.json file
        simulation_width: Width of the simulation area
        simulation_height: Height of the simulation area

    Returns:
        Tuple: (list_of_wall_rects, list_of_exit_rects)
               Returns ([], []) if grid loading fails.
    """
    # Load the grid
    grid = load_grid_from_json(grid_file)
    if grid is None:
        print("Warning: Failed to load grid. Returning empty walls/exits.")
        return [], [] # Return empty lists on failure


    # Calculate scale factors to match simulation dimensions
    grid_height = len(grid)
    grid_width = len(grid[0])
    # Ensure grid dimensions are valid
    if grid_height == 0 or grid_width == 0:
        print("Warning: Loaded grid has zero dimensions. Returning empty walls/exits.")
        return [], []

    scale_x = simulation_width / grid_width
    scale_y = simulation_height / grid_height

    avg_scale = (scale_x + scale_y) / 2.0
    walls, exits = convert_grid_to_elements(grid, avg_scale) # Use average scale factor

    print(f"Loaded {len(walls)} wall cells and {len(exits)} exit cells from grid.")
    return walls, exits # Return lists of pygame.Rect