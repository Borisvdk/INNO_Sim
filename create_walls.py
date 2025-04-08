import json

grid_width = 60
grid_height = 40
white = [255, 255, 255]
black = [0, 0, 0]

# Initialize grid with all white cells
grid = [[list(white) for _ in range(grid_width)] for _ in range(grid_height)] # Use list() to ensure mutable copies

# --- Define Walls ---

# 1. Outer walls
for x in range(grid_width):
    grid[0][x] = list(black)
    grid[grid_height - 1][x] = list(black)
for y in range(grid_height):
    grid[y][0] = list(black)
    grid[y][grid_width - 1] = list(black)

# 2. Exit (Overwrite part of top wall)
# Corresponds roughly to sim coords x=500-580 if sim_width=600
exit_start_col = 50
exit_end_col = 58 # Exclusive
for x in range(exit_start_col, exit_end_col):
     if 0 <= x < grid_width:
        grid[0][x] = list(white) # Make exit white

# 3. Central Corridor walls (horizontal)
corridor_wall_y1 = 11 # Top wall of lower rooms / floor of upper rooms
corridor_wall_y2 = 28 # Floor of lower rooms / ceiling of rooms below
door_cols = [5, 15, 25, 35, 45, 55] # Where doorways will be
door_width = 2 # How many cells wide is the doorway

for y_wall in [corridor_wall_y1, corridor_wall_y2]:
    is_door = False
    for x in range(1, grid_width - 1): # Don't overwrite outer walls
        is_door = False
        for door_start in door_cols:
            if door_start <= x < door_start + door_width:
                is_door = True
                break
        if not is_door:
            grid[y_wall][x] = list(black)

# 4. Vertical Room walls
room_wall_cols = [10, 20, 30, 40, 50]
for x_wall in room_wall_cols:
    # Wall above corridor (up to corridor wall 1)
    for y in range(1, corridor_wall_y1):
        grid[y][x_wall] = list(black)
    # Wall below corridor (from corridor wall 2 down to bottom wall)
    for y in range(corridor_wall_y2 + 1, grid_height - 1):
        grid[y][x_wall] = list(black)

# --- Generate JSON Output ---
# Use dumps for correct formatting, though it won't have newlines per row by default
# For readability matching the original request, manual formatting or a custom print is needed.
# Let's create the string representation manually for perfect match.

json_string = "[\n"
for y in range(grid_height):
    json_string += "  ["
    for x in range(grid_width):
        json_string += f"[{grid[y][x][0]}, {grid[y][x][1]}, {grid[y][x][2]}]"
        if x < grid_width - 1:
            json_string += ", "
    json_string += "]"
    if y < grid_height - 1:
        json_string += ",\n"
    else:
        json_string += "\n"
json_string += "]"

# --- Save to file ---
try:
    with open("grid.json", "w") as f:
        f.write(json_string)
    print("Successfully generated and saved corrected grid.json")
except Exception as e:
    print(f"Error saving grid.json: {e}")

