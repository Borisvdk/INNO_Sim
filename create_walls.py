import json

grid_width = 60
grid_height = 40
white = [255, 255, 255]
black = [0, 0, 0]


grid = [[list(white) for _ in range(grid_width)] for _ in range(grid_height)]


for x in range(grid_width):
    grid[0][x] = list(black)
    grid[grid_height - 1][x] = list(black)
for y in range(grid_height):
    grid[y][0] = list(black)
    grid[y][grid_width - 1] = list(black)


exit_start_col = 50
exit_end_col = 58
for x in range(exit_start_col, exit_end_col):
     if 0 <= x < grid_width:
        grid[0][x] = list(white)


corridor_wall_y1 = 11
corridor_wall_y2 = 28
door_cols = [5, 15, 25, 35, 45, 55]
door_width = 2

for y_wall in [corridor_wall_y1, corridor_wall_y2]:
    is_door = False
    for x in range(1, grid_width - 1):
        is_door = False
        for door_start in door_cols:
            if door_start <= x < door_start + door_width:
                is_door = True
                break
        if not is_door:
            grid[y_wall][x] = list(black)


room_wall_cols = [10, 20, 30, 40, 50]
for x_wall in room_wall_cols:
    for y in range(1, corridor_wall_y1):
        grid[y][x_wall] = list(black)
    for y in range(corridor_wall_y2 + 1, grid_height - 1):
        grid[y][x_wall] = list(black)


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


try:
    with open("grid.json", "w") as f:
        f.write(json_string)
    print("Successfully generated and saved corrected grid.json")
except Exception as e:
    print(f"Error saving grid.json: {e}")