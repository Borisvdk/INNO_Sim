import math
import random

from agents.adultagent import AdultAgent
from agents.studentagent import StudentAgent
from agents.schoolagent import SpatialGrid


class SchoolModel:
    def __init__(self, n_students=50, n_adults=10, width=100, height=100):
        self.num_students = n_students
        self.num_adults = n_adults
        self.width = width
        self.height = height
        self.running = True
        self.schedule = []  # List of all agents
        self.active_shots = []  # List to store active shots
        self.simulation_time = 0.0  # Total simulated time

        # Initialize spatial grid
        self.spatial_grid = SpatialGrid(width, height, cell_size=10)

        # Walls definition remains unchanged
        self.walls = [
            (20, 20, 580, 22),  # top
            (20, 195, 250, 197),  # middle left
            (340, 195, 580, 197),  # middle right
            (20, 375, 580, 377),  # bottom
            (20, 20, 22, 375),  # left
            (578, 20, 580, 375),  # right
        ]
        self.wall_grid = {}
        self._create_wall_grid()

        # Create student agents
        for i in range(self.num_students):
            x = random.uniform(5, self.width - 5)
            y = random.uniform(5, self.height - 5)
            student = StudentAgent(i, self, (x, y), "student", self.schedule)
            self.schedule.append(student)

        # Create adult agents
        for i in range(self.num_adults):
            x = random.uniform(5, self.width - 5)
            y = random.uniform(5, self.height - 5)
            adult = AdultAgent(i + self.num_students, self, (x, y), "adult", self.schedule)
            self.schedule.append(adult)

        # Select one student as the shooter after all agents are created
        self.select_shooter()

    def select_shooter(self):
        """Randomly select one student to be the shooter."""
        students = [agent for agent in self.schedule if agent.agent_type == "student"]
        if students:
            shooter = random.choice(students)
            shooter.is_shooter = True
            shooter.has_weapon = True

    def _create_wall_grid(self):
        """Create a grid-based lookup for walls to optimize wall avoidance checks"""
        for wall_idx, wall in enumerate(self.walls):
            x_min, y_min, x_max, y_max = wall

            # Determine grid cells this wall intersects (using 10x10 grid for the entire space)
            x_min_grid = int(max(0, x_min / self.width * 10))
            x_max_grid = int(min(9, x_max / self.width * 10))
            y_min_grid = int(max(0, y_min / self.height * 10))
            y_max_grid = int(min(9, y_max / self.height * 10))

            # Add wall index to all intersecting grid cells
            for x_grid in range(x_min_grid, x_max_grid + 1):
                for y_grid in range(y_min_grid, y_max_grid + 1):
                    grid_key = (x_grid, y_grid)
                    if grid_key not in self.wall_grid:
                        self.wall_grid[grid_key] = set()
                    self.wall_grid[grid_key].add(wall_idx)

    def step_continuous(self, dt):
        """Voer een continue tijdstap uit met delta tijd dt."""
        # Update de totale simulatietijd
        self.simulation_time += dt

        # Clear and rebuild spatial grid
        self.spatial_grid.clear()
        for agent in self.schedule:
            self.spatial_grid.add_agent(agent)

        # Activeer alle agenten in willekeurige volgorde met delta tijd
        random.shuffle(self.schedule)
        for agent in self.schedule:
            agent.step_continuous(dt)

        # Update spatial grid after all agents have moved
        self.spatial_grid.clear()
        for agent in self.schedule:
            self.spatial_grid.add_agent(agent)

    def remove_agent(self, agent):
        """Verwijder een agent uit de simulatie."""
        if agent in self.schedule:
            self.schedule.remove(agent)