import pygame
import math
import heapq

# Initialize Pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("School Evacuation Simulation")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GRAY = (200, 200, 200)

# Simulation settings
FPS = 60
AGENT_SPEED = 2

# Walls setup (x, y, width, height)
walls = [
    pygame.Rect(200, 150, 400, 20),
    pygame.Rect(200, 300, 20, 200),
    pygame.Rect(580, 150, 20, 200),
    pygame.Rect(300, 450, 200, 20),
    pygame.Rect(100, 100, 150, 20),
    pygame.Rect(550, 100, 150, 20),
    pygame.Rect(400, 250, 200, 20),
    pygame.Rect(400, 350, 200, 20),
    pygame.Rect(150, 400, 150, 20),
]

# Student agent class
class Student:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.path = []
        self.reached_exit = False

    def move(self):
        if self.path:
            target_x, target_y = self.path[0]
            dx, dy = target_x - self.x, target_y - self.y
            dist = math.hypot(dx, dy)
            
            if dist < AGENT_SPEED:
                self.x, self.y = target_x, target_y
                self.path.pop(0)
            else:
                self.x += AGENT_SPEED * dx / dist
                self.y += AGENT_SPEED * dy / dist

    def draw(self):
        pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), 5)

    def at_exit(self):
        return self.x <= 0 or self.x >= WIDTH or self.y <= 0 or self.y >= HEIGHT

def astar(start, goal, walls):
    """Finds the shortest path from start to goal using A* while avoiding walls."""
    
    def heuristic(a, b):
        """Euclidean distance heuristic function."""
        return math.hypot(a[0] - b[0], a[1] - b[1])

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}

    while open_set:
        _, current = heapq.heappop(open_set)

        # Stop if we are close enough to the goal
        if heuristic(current, goal) < 10:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        # Generate more neighbor points with finer granularity
        step_size = 5  # Reduced step size for better accuracy
        directions = [
            (step_size, 0), (-step_size, 0), (0, step_size), (0, -step_size),
            (step_size, step_size), (-step_size, step_size),
            (step_size, -step_size), (-step_size, -step_size)
        ]

        for dx, dy in directions:
            neighbor = (current[0] + dx, current[1] + dy)

            # Ensure neighbor is inside screen boundaries
            if not (0 <= neighbor[0] <= WIDTH and 0 <= neighbor[1] <= HEIGHT):
                continue

            # Collision check with walls
            point_rect = pygame.Rect(neighbor[0] - 2, neighbor[1] - 2, 4, 4)
            if any(point_rect.colliderect(wall) for wall in walls):
                continue

            # Update pathfinding scores
            tentative_g_score = g_score[current] + heuristic(current, neighbor)

            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))

    return []  # No valid path found

def main():
    clock = pygame.time.Clock()
    # Added more students at various positions
    students = [
        Student(100, 100),
        Student(150, 200),
        Student(400, 500),
        Student(300, 350),
        Student(700, 500),
        Student(600, 200),
        Student(250, 400),
        Student(500, 150),
    ]
    
    emergency = False

    running = True
    while running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                emergency = True
                for student in students:
                    exits = [
                        (student.x, 0),              # Top edge
                        (student.x, HEIGHT),         # Bottom edge
                        (0, student.y),              # Left edge
                        (WIDTH, student.y)          # Right edge
                    ]
                    closest_exit = min(exits, key=lambda ex: math.hypot(student.x - ex[0], student.y - ex[1]))
                    path = astar((student.x, student.y), closest_exit, walls)
                    if path:
                        student.path = path
                    else:
                        print(f"No path found for student at ({student.x}, {student.y})")

        screen.fill(WHITE)

        for wall in walls:
            pygame.draw.rect(screen, BLACK, wall)

        for student in students[:]:
            student.move()
            student.draw()
            if student.at_exit():
                students.remove(student)  # Remove student who exits

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
