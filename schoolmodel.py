import math
import random
import os
from grid_converter import integrate_grid_into_simulation
import config
import pygame
from dijkstra_test import astar
import config

HEIGHT, WIDTH = config.SCREEN_HEIGHT, config.SCREEN_WIDTH


class AgentFactory:
    """Factory class for creating different types of agents."""

    @staticmethod
    def create_agent(agent_type, unique_id, model, position, is_shooter=False):
        """Create and return an agent of the specified type."""
        if agent_type == "student":
            from agents.studentagent import StudentAgent
            agent = StudentAgent(unique_id, model, position, agent_type)
            if is_shooter:
                agent.is_shooter = True
                agent.has_weapon = True
            return agent
        elif agent_type == "adult":
            from agents.adultagent import AdultAgent
            return AdultAgent(unique_id, model, position, agent_type)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")


class SpatialGrid:
    """An optimized grid-based spatial partitioning system for efficiently finding nearby agents."""

    def __init__(self, width, height, cell_size):
        self.cell_size = cell_size
        self.grid_width = math.ceil(width / cell_size)
        self.grid_height = math.ceil(height / cell_size)
        self.grid = {}  # Dictionary of {(cell_x, cell_y): [agents]}
        self.agent_positions = {}  # Track each agent's last position and cell: {agent: ((x,y), (cell_x, cell_y))}

    def clear(self):
        """Clear all cells in the grid."""
        self.grid = {}
        self.agent_positions = {}

    def _get_cell_indices(self, position):
        """Convert a position to grid cell indices."""
        x, y = position
        cell_x = int(x / self.cell_size)
        cell_y = int(y / self.cell_size)
        return cell_x, cell_y

    def update_agent(self, agent):
        """Update an agent's position in the grid, only if needed."""
        current_position = agent.position
        current_cell = self._get_cell_indices(current_position)

        # Check if we've seen this agent before and if it moved cells
        if agent in self.agent_positions:
            last_position, last_cell = self.agent_positions[agent]

            # If cell hasn't changed, do nothing
            if last_cell == current_cell:
                self.agent_positions[agent] = (current_position, current_cell)
                return

            # Remove from old cell
            if last_cell in self.grid and agent in self.grid[last_cell]:
                self.grid[last_cell].remove(agent)
                if not self.grid[last_cell]:  # Clean up empty cells
                    del self.grid[last_cell]

        # Add to new cell
        if current_cell not in self.grid:
            self.grid[current_cell] = []
        self.grid[current_cell].append(agent)

        # Update tracked position
        self.agent_positions[agent] = (current_position, current_cell)

    def remove_agent(self, agent):
        """Remove an agent from the grid."""
        if agent in self.agent_positions:
            _, cell = self.agent_positions[agent]
            if cell in self.grid and agent in self.grid[cell]:
                self.grid[cell].remove(agent)
                if not self.grid[cell]:  # Clean up empty cells
                    del self.grid[cell]
            del self.agent_positions[agent]

    def get_nearby_agents(self, position, radius):
        """Get all agents within a certain radius of a position."""
        center_x, center_y = position
        cell_radius = math.ceil(radius / self.cell_size)
        cell_x, cell_y = self._get_cell_indices(position)

        nearby_agents = []

        # Check all cells in the region
        for dx in range(-cell_radius, cell_radius + 1):
            for dy in range(-cell_radius, cell_radius + 1):
                cell_key = (cell_x + dx, cell_y + dy)
                if cell_key in self.grid:
                    nearby_agents.extend(self.grid[cell_key])

        return nearby_agents


class SchoolModel:
    def __init__(self, n_students=config.INITIAL_STUDENTS, n_adults=config.INITIAL_ADULTS,
                 width=config.SIM_WIDTH, height=config.SIM_HEIGHT,
                 adult_weapon_percentage=config.ADULT_WEAPON_PROBABILITY,
                 grid_file=None):
        """
        Initialize the school simulation model.

        Args:
            n_students (int): Number of student agents.
            n_adults (int): Number of adult agents.
            width (float): Width of the simulation area.
            height (float): Height of the simulation area.
            adult_weapon_percentage (float): Probability an adult has a weapon.
            grid_file (str, optional): Path to a grid file for walls.
        """
        self.num_students = n_students
        self.num_adults = n_adults
        self.width = width
        self.height = height
        self.adult_weapon_percentage = adult_weapon_percentage
        self.running = True
        self.schedule = []  # List of all agents
        self.active_shots = []  # List to store active shots (e.g., projectiles)
        self.simulation_time = 0.0  # Total simulated time in seconds
        self.active_shooters = set()  # Set to track all active shooters
        self.tick_count = 0
        self.shooter_check_interval = config.SHOOTER_CHECK_INTERVAL
        self.last_shooter_check_time = 0.0
        self.shooter_emergence_probability = config.SHOOTER_EMERGENCE_PROBABILITY
        self.spatial_grid = SpatialGrid(width, height, cell_size=10)  # Assumed spatial grid utility

        # Load walls from grid file or use default configuration
        if grid_file and os.path.exists(grid_file):
            print(f"Loading walls from grid file: {grid_file}")
            self.walls = integrate_grid_into_simulation(grid_file, width, height)
            print(f"Loaded {len(self.walls)} wall segments from grid file")
        else:
            print("Using default wall configuration")
            self.walls = [
                (20, 20, 500, 22),  # Top wall (horizontal)
                (20, 195, 250, 197),  # Middle left (horizontal)
                (340, 195, 580, 197),  # Middle right (horizontal)
                (20, 375, 580, 377),  # Bottom wall (horizontal)
                (20, 20, 22, 375),  # Left wall (vertical)
                (578, 20, 580, 375),  # Right wall (vertical)
            ]

        self._create_wall_grid()
        self._create_all_agents()

    def _create_all_agents(self):
        """Create all agents at safe positions - no shooter at the beginning"""
        # Generate safe positions for all agents ahead of time
        all_positions = []
        min_distance_between_agents = 8.0  # Ensure agents aren't too close to each other

        for _ in range(self.num_students + self.num_adults):
            # Generate a new position that's not too close to existing agents or walls
            for attempt in range(100):  # Limit attempts to prevent infinite loops
                position = self.generate_safe_position(min_wall_distance=5.0)

                # Check if too close to other agents
                too_close = False
                for existing_pos in all_positions:
                    dx = position[0] - existing_pos[0]
                    dy = position[1] - existing_pos[1]
                    if dx * dx + dy * dy < min_distance_between_agents ** 2:
                        too_close = True
                        break

                if not too_close:
                    all_positions.append(position)
                    break

            # Fallback if we couldn't find a good position
            if attempt == 99 and too_close:
                print("Warning: Could not find position far enough from other agents")
                all_positions.append(position)  # Use the last attempt

        # Create student agents with safe positions - no shooter initially
        for i in range(self.num_students):
            position = all_positions[i]
            agent = AgentFactory.create_agent("student", i, self, position, is_shooter=False)
            self.schedule.append(agent)
            self.spatial_grid.update_agent(agent)

        # Create adult agents with safe positions
        for i in range(self.num_adults):
            position = all_positions[i + self.num_students]
            agent = AgentFactory.create_agent("adult", i + self.num_students, self, position)
            # Controleer of deze volwassen agent een wapen krijgt:
            if random.random() < self.adult_weapon_percentage:
                agent.has_weapon = True
                agent.color = (255, 255, 0)  # Gele kleur
            # Indien geen wapen, blijft de agent zijn standaardkleur behouden
            self.schedule.append(agent)
            self.spatial_grid.update_agent(agent)

    def _create_wall_grid(self):
        """Create a grid-based lookup for walls to optimize wall avoidance checks"""
        self.wall_grid = {}

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
        """Perform a continuous time step with delta time dt."""
        # Update the total simulation time
        self.simulation_time += dt

        # Check for random shooter emergence
        if not self.has_active_shooter and self.simulation_time - self.last_shooter_check_time >= self.shooter_check_interval:
            self.last_shooter_check_time = self.simulation_time
            self._check_for_shooter_emergence()

        if self.has_active_shooter:
            self.run_to_exit()

        # Activate all agents in random order with delta time
        random.shuffle(self.schedule)
        for agent in self.schedule:
            agent.step_continuous(dt)

    def _check_for_shooter_emergence(self):
        """Check if a random student spontaneously becomes a shooter."""
        if random.random() > self.shooter_emergence_probability:
            return
        student_agents = [
            agent for agent in self.schedule
            if agent.agent_type == "student" and not agent.is_shooter
        ]
        if not student_agents:
            return
        random_student = random.choice(student_agents)
        random_student.is_shooter = True
        random_student.has_weapon = True
        self.active_shooters.add(random_student)
        print(f"ALERT: Student {random_student.unique_id} has become an active shooter "
              f"at time {self.simulation_time:.1f}s")

    def add_manual_shooter(self):
        """Manually convert a random student into a shooter."""
        student_agents = [
            agent for agent in self.schedule
            if agent.agent_type == "student" and not agent.is_shooter
        ]
        if not student_agents:
            print("No eligible students available to become a shooter.")
            return False
        random_student = random.choice(student_agents)
        random_student.is_shooter = True
        random_student.has_weapon = True
        self.active_shooters.add(random_student)
        print(f"MANUAL ALERT: Student {random_student.unique_id} has become an active shooter "
              f"at time {self.simulation_time:.1f}s")
        return True

    @property
    def has_active_shooter(self):
        """Check if there is at least one active shooter."""
        return len(self.active_shooters) > 0

    def add_students(self, count):
        """Add a specified number of students to the simulation."""
        for _ in range(count):
            position = self.generate_safe_position(min_wall_distance=5.0)
            agent = AgentFactory.create_agent("student", len(self.schedule), self, position)
            self.schedule.append(agent)
            self.spatial_grid.update_agent(agent)

    def add_adults(self, count):
        """Add a specified number of adults to the simulation."""
        for _ in range(count):
            position = self.generate_safe_position(min_wall_distance=5.0)
            agent = AgentFactory.create_agent("adult", len(self.schedule), self, position)
            self.schedule.append(agent)
            self.spatial_grid.update_agent(agent)

    def generate_safe_position(self, min_wall_distance=5.0, max_attempts=100):
        """
        Generate a random position that's not inside or too close to a wall.

        Args:
            min_wall_distance: Minimum distance from any wall
            max_attempts: Maximum number of attempts before giving up

        Returns:
            Tuple (x, y) of the safe position
        """
        padding = max(5.0, min_wall_distance)  # Minimum padding from walls

        for _ in range(max_attempts):
            # Generate random position with padding from edges
            x = random.uniform(padding, self.width - padding)
            y = random.uniform(padding, self.height - padding)

            # Check if position is safe (not too close to any wall)
            if self.is_position_safe((x, y), min_wall_distance):
                return (x, y)

        # If we can't find a safe position after max attempts, find the safest available
        print("Warning: Could not find ideal safe position after", max_attempts, "attempts")
        return self.find_safest_position(padding)

    def is_position_safe(self, position, min_wall_distance=5.0):
        """
        Check if a position is at a safe distance from all walls.

        Args:
            position: Tuple (x, y) to check
            min_wall_distance: Minimum distance from any wall

        Returns:
            True if position is safe, False otherwise
        """
        x, y = position

        # First quick check - are we inside any wall?
        for wall in self.walls:
            wall_x1, wall_y1, wall_x2, wall_y2 = wall
            if (wall_x1 <= x <= wall_x2 and wall_y1 <= y <= wall_y2):
                return False  # Inside a wall

        # Then check distance to each wall
        for wall in self.walls:
            wall_x1, wall_y1, wall_x2, wall_y2 = wall

            # Calculate the closest point on the wall
            closest_x = max(wall_x1, min(x, wall_x2))
            closest_y = max(wall_y1, min(y, wall_y2))

            # Calculate distance to the closest point
            dx = x - closest_x
            dy = y - closest_y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < min_wall_distance:
                return False  # Too close to a wall

        return True

    def find_safest_position(self, padding):
        """
        Find the position with maximum distance to any wall.
        Used as a fallback when generate_safe_position fails.

        Args:
            padding: Minimum padding from edges

        Returns:
            Tuple (x, y) of the safest position
        """
        # Create a grid of candidate positions
        grid_size = 20  # 20x20 grid
        candidates = []

        for i in range(grid_size):
            for j in range(grid_size):
                x = padding + (self.width - 2 * padding) * i / (grid_size - 1)
                y = padding + (self.height - 2 * padding) * j / (grid_size - 1)

                # Calculate minimum distance to any wall
                min_distance = float('inf')
                inside_wall = False

                for wall in self.walls:
                    wall_x1, wall_y1, wall_x2, wall_y2 = wall

                    # Check if inside wall
                    if (wall_x1 <= x <= wall_x2 and wall_y1 <= y <= wall_y2):
                        inside_wall = True
                        break

                    closest_x = max(wall_x1, min(x, wall_x2))
                    closest_y = max(wall_y1, min(y, wall_y2))

                    dx = x - closest_x
                    dy = y - closest_y
                    distance = math.sqrt(dx * dx + dy * dy)

                    min_distance = min(min_distance, distance)

                # Inside a wall? Skip
                if inside_wall:
                    continue

                candidates.append((x, y, min_distance))

        # Sort by distance (largest first)
        candidates.sort(key=lambda c: -c[2])

        # Return the position with the maximum distance, or a default if no candidates
        if candidates:
            return (candidates[0][0], candidates[0][1])
        else:
            print("Warning: No safe position found, using center of the space.")
            return (self.width / 2, self.height / 2)

    def remove_agent(self, agent):
        """Remove an agent from the simulation."""
        if agent in self.schedule:
            if agent in self.active_shooters:
                self.active_shooters.remove(agent)
                print(f"Shooter {agent.unique_id} has been removed. Active shooters left: {len(self.active_shooters)}")
            self.spatial_grid.remove_agent(agent)
            self.schedule.remove(agent)


    def run_to_exit(self):
        """Gradually makes students start fleeing, one per tick, to avoid lag."""
        
        # Define the school exit
        school_exit = pygame.Rect(500, 18, 80, 6)  # Slightly larger for better detection

        # Convert walls to pygame.Rect objects for collision detection
        wall_rects = [pygame.Rect(x1, y1, x2 - x1, y2 - y1) for (x1, y1, x2, y2) in self.walls]

        # Find students who haven't started fleeing yet
        non_fleeing_students = [s for s in self.schedule if s.agent_type == "student" and not s.in_emergency]

        # If there are students left to start fleeing, pick one at random
        if non_fleeing_students:
            if self.tick_count >= 5:
                self.tick_count = 0
                student = random.choice(non_fleeing_students)
                print(f"🚨 Student at {student.position} is now evacuating.")

                # Find the path to the single exit
                exit_point = (540, 20)  # Center of the exit
                path = astar((student.position[0], student.position[1]), exit_point, wall_rects)

                if path:
                    student.path = path
                    student.in_emergency = True  # Mark student as actively fleeing
                else:
                    print(f"⚠ No path found for student at {student.position}")
            else:
                self.tick_count += 1

