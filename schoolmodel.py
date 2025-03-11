import math
import random

from agents.adultagent import AdultAgent
from agents.studentagent import StudentAgent
from agents.schoolagent import SpatialGrid


class SchoolModel:
    """Model klasse voor de school simulatie."""

    def __init__(self, n_students=50, n_adults=10, width=100, height=100):
        self.num_students = n_students
        self.num_adults = n_adults
        self.width = width
        self.height = height
        self.running = True
        self.schedule = []  # Lijst van alle agenten
        self.simulation_time = 0.0  # Totale gesimuleerde tijd

        # Initialize spatial grid for efficient agent queries
        # Cell size should be larger than the personal space radius of agents
        self.spatial_grid = SpatialGrid(width, height, cell_size=10)

        # Voeg muren toe
        self.walls = [
            (20, 20, 580, 22),  # boven
            (20, 195, 250, 197),  # midden links
            (340, 195, 580, 197),  # midden rechts
            (20, 375, 580, 377),  # onder
            (20, 20, 22, 375),  # links
            (578, 20, 580, 375),  # rechts
        ]

        # Create a grid for wall lookups
        self.wall_grid = {}
        self._create_wall_grid()

        # Maak student agenten
        for i in range(self.num_students):
            x = random.uniform(5, self.width - 5)  # Kleine marge
            y = random.uniform(5, self.height - 5)  # Kleine marge
            student = StudentAgent(i, self, (x, y), "student", self.schedule)
            self.schedule.append(student)

        # Maak volwassen agenten
        for i in range(self.num_adults):
            x = random.uniform(5, self.width - 5)
            y = random.uniform(5, self.height - 5)
            adult = AdultAgent(i + self.num_students, self, (x, y), "adult", self.schedule)
            self.schedule.append(adult)

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