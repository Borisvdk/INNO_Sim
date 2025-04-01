import pygame
import json

# Grid settings
GRID_SIZE = 10  # Size of each grid cell in pixels
GRID_WIDTH = 120  # Number of columns
GRID_HEIGHT = 80  # Number of rows

# Colors
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)  # Define red color

# Available colors
COLOR_MAP = {1: WHITE, 2: BLACK, 3: GREEN, 4: RED}  # Add red to the color map

# Initialize grid with all white (empty space)
grid = [[WHITE for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

# Default drawing color
current_color = BLACK
show_grid = True  # Flag to show/hide grid lines


def save_grid(filename="grid.json"):
    with open(filename, "w") as f:
        json.dump(grid, f)
    print(grid_to_wall_coords(grid))
    print("Grid saved!")
    
#
def grid_to_wall_coords(grid):
    walls = []
    rows = len(grid)
    cols = len(grid[0])

    # Check for horizontal walls
    for r in range(rows):
        start = None
        for c in range(cols):
            if grid[r][c] == 1:
                if start is None:
                    start = c  # Found start of horizontal wall
            if grid[r][c] == 0 or c == cols - 1:  # End of wall or end of row
                if start is not None:
                    if c == cols - 1 and grid[r][c] == 1:  # last cell is part of wall
                        end = c
                    else:
                        end = c - 1
                    walls.append((start, r, end, r))
                    start = None

    # Check for vertical walls
    for c in range(cols):
        start = None
        for r in range(rows):
            if grid[r][c] == 1:
                if start is None:
                    start = r  # Found start of vertical wall
            if grid[r][c] == 0 or r == rows - 1:  # End of wall or end of column
                if start is not None:
                    if r == rows - 1 and grid[r][c] == 1:  # last cell is part of wall
                        end = r
                    else:
                        end = r - 1
                    walls.append((c, start, c, end))
                    start = None

    return walls


def load_grid(filename="grid.json"):
    global grid
    try:
        with open(filename, "r") as f:
            grid = json.load(f)
        print("Grid loaded!")
    except FileNotFoundError:
        print("No saved grid found.")


def draw_grid(screen):
    """Draw the grid with or without lines based on the show_grid flag."""
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            rect = pygame.Rect(x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
            pygame.draw.rect(screen, grid[y][x], rect)
            if show_grid:
                pygame.draw.rect(screen, GRAY, rect, 1)  # Grid lines


def draw_pause_menu(screen):
    """Display the pause menu."""
    menu_bg = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    menu_bg.fill((0, 0, 0, 180))  # Transparent dark overlay
    screen.blit(menu_bg, (0, 0))

    font = pygame.font.Font(None, 40)
    text1 = font.render("PAUSED", True, WHITE)
    text2 = font.render("S: Save Map", True, WHITE)
    text3 = font.render("T: Toggle Grid", True, WHITE)
    text4 = font.render("Esc: Resume", True, WHITE)

    screen.blit(text1, (150, 100))
    screen.blit(text2, (150, 160))
    screen.blit(text3, (150, 220))
    screen.blit(text4, (150, 280))

    pygame.display.flip()


def main():
    global current_color, show_grid
    pygame.init()
    screen = pygame.display.set_mode((GRID_WIDTH * GRID_SIZE, GRID_HEIGHT * GRID_SIZE))
    pygame.display.set_caption("Grid Map Maker")

    running = True
    paused = False
    mouse_held = False  # Track if the mouse is being held down

    while running:
        screen.fill(WHITE)
        draw_grid(screen)

        if paused:
            draw_pause_menu(screen)
        else:
            pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s and paused:
                    save_grid()
                elif event.key == pygame.K_l and not paused:
                    load_grid()
                elif event.key == pygame.K_p:
                    paused = True  # Open pause menu
                elif event.key == pygame.K_ESCAPE:
                    paused = False  # Close pause menu
                elif event.key == pygame.K_t and paused:
                    show_grid = not show_grid  # Toggle grid lines
                elif event.key == pygame.K_1:
                    current_color = WHITE
                elif event.key == pygame.K_2:
                    current_color = BLACK
                elif event.key == pygame.K_3:
                    current_color = GREEN
                elif event.key == pygame.K_4:  # Switch to red
                    current_color = RED

            if not paused:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_held = True
                    x, y = pygame.mouse.get_pos()
                    grid_x, grid_y = x // GRID_SIZE, y // GRID_SIZE
                    if 0 <= grid_x < GRID_WIDTH and 0 <= grid_y < GRID_HEIGHT:
                        grid[grid_y][grid_x] = current_color

                elif event.type == pygame.MOUSEBUTTONUP:
                    mouse_held = False

                elif event.type == pygame.MOUSEMOTION and mouse_held:
                    x, y = pygame.mouse.get_pos()
                    grid_x, grid_y = x // GRID_SIZE, y // GRID_SIZE
                    if 0 <= grid_x < GRID_WIDTH and 0 <= grid_y < GRID_HEIGHT:
                        grid[grid_y][grid_x] = current_color

    pygame.quit()


if __name__ == "__main__":
    main()
