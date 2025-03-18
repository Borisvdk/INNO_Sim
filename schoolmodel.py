import math
import random


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
    """Main model class for the school simulation."""

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

        # Define walls (can be replaced with more complex layout)
        self.walls = [
            (20, 20, 580, 22),  # top wall (horizontal)
            (20, 195, 250, 197),  # middle left (horizontal)
            (340, 195, 580, 197),  # middle right (horizontal)
            (20, 375, 580, 377),  # bottom wall (horizontal)
            (20, 20, 22, 375),  # left wall (vertical)
            (578, 20, 580, 375),  # right wall (vertical)
        ]

        # Create wall grid structures
        self._create_wall_grid()

        # Create all agents with safe positions
        self._create_all_agents()

    def _create_all_agents(self):
        """Create all agents at safe positions"""
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

        # Choose shooter index
        shooter_index = random.randint(0, self.num_students - 1) if self.num_students > 0 else -1

        # Create student agents with safe positions
        for i in range(self.num_students):
            position = all_positions[i]
            is_shooter = (i == shooter_index)
            agent = AgentFactory.create_agent("student", i, self, position, is_shooter)
            self.schedule.append(agent)
            self.spatial_grid.update_agent(agent)

        # Create adult agents with safe positions
        for i in range(self.num_adults):
            position = all_positions[i + self.num_students]
            agent = AgentFactory.create_agent("adult", i + self.num_students, self, position)
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

        # Activate all agents in random order with delta time
        random.shuffle(self.schedule)
        for agent in self.schedule:
            agent.step_continuous(dt)

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
            # Remove from spatial grid first
            self.spatial_grid.remove_agent(agent)
            # Then remove from schedule
            self.schedule.remove(agent)