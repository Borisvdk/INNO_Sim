import pygame
import math
import heapq


pygame.init()


WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("School Evacuation Simulation")


WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GRAY = (200, 200, 200)


FPS = 60
AGENT_SPEED = 2


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


class Student:
    """Represents a student agent in the simplified A* example simulation."""
    def __init__(self, x, y):
        """
        Initialize a Student for the A* example.

        Args:
            x (int): Initial x-coordinate.
            y (int): Initial y-coordinate.
        """
        self.x = x
        self.y = y
        self.path = []
        self.reached_exit = False

    def move(self):
        """Move the student along its calculated path."""
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
        """Draw the student on the screen."""
        pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), 5)

    def at_exit(self):
        """
        Check if the student has reached the boundary considered an exit.

        Returns:
            bool: True if the student is at or beyond the screen boundaries.
        """
        return self.x <= 0 or self.x >= WIDTH or self.y <= 0 or self.y >= HEIGHT

def astar(start, goal, walls):
    """
    Finds the shortest path from start to goal using the A* algorithm, avoiding walls.

    Args:
        start (tuple): The starting (x, y) coordinates.
        goal (tuple): The target (x, y) coordinates.
        walls (list): A list of pygame.Rect objects representing obstacles.

    Returns:
        list: A list of (x, y) tuples representing the path, or an empty list if no path is found.
    """

    def heuristic(a, b):
        """
        Calculate the Euclidean distance heuristic between two points.

        Args:
            a (tuple): The first point (x, y).
            b (tuple): The second point (x, y).

        Returns:
            float: The Euclidean distance.
        """
        return math.hypot(a[0] - b[0], a[1] - b[1])

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}

    while open_set:
        _, current = heapq.heappop(open_set)

        if heuristic(current, goal) < 10:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        step_size = 5
        directions = [
            (step_size, 0), (-step_size, 0), (0, step_size), (0, -step_size),
            (step_size, step_size), (-step_size, step_size),
            (step_size, -step_size), (-step_size, -step_size)
        ]

        for dx, dy in directions:
            neighbor = (current[0] + dx, current[1] + dy)

            if not (0 <= neighbor[0] <= WIDTH and 0 <= neighbor[1] <= HEIGHT):
                continue

            point_rect = pygame.Rect(neighbor[0] - 2, neighbor[1] - 2, 4, 4)
            if any(point_rect.colliderect(wall) for wall in walls):
                continue

            tentative_g_score = g_score[current] + heuristic(current, neighbor)

            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))

    return []

def main():
    """Main function to run the simple A* demonstration."""
    clock = pygame.time.Clock()
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
                        (student.x, 0),
                        (student.x, HEIGHT),
                        (0, student.y),
                        (WIDTH, student.y)
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
                students.remove(student)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()