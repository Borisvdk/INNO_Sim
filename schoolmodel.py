import math
import random


class AgentFactory:
    """Factory class for creating different types of agents."""

    @staticmethod
    def create_agent(agent_type, unique_id, model, position, is_shooter=False):
        """Create and return an agent of the specified type."""
        if agent_type == "student":
            from agents.studentagent import StudentAgent
            agent = StudentAgent(unique_id, model, position, agent_type, model.schedule)
            if is_shooter:
                agent.is_shooter = True
                agent.has_weapon = True
            return agent
        elif agent_type == "adult":
            from agents.adultagent import AdultAgent
            return AdultAgent(unique_id, model, position, agent_type, model.schedule)
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

        # Walls definition
        self.walls = [
            (20, 20, 580, 22),  # top
            (20, 195, 250, 197),  # middle left
            (340, 195, 580, 197),  # middle right
            (20, 375, 580, 377),  # bottom
            (20, 20, 22, 375),  # left
            (578, 20, 580, 375),  # right
        ]

        # Create optimized wall distance grid
        self._create_wall_grid()

        # Create all agents in one pass
        self._create_all_agents()

    def _create_wall_grid(self):
        """Create wall grid structures for collision detection and avoidance"""
        # Create the original wall_grid for backward compatibility
        self.wall_grid = {}
        grid_size = 10  # 10x10 grid for the entire space

        # Populate the original wall_grid structure
        for wall_idx, wall in enumerate(self.walls):
            x_min, y_min, x_max, y_max = wall

            # Determine grid cells this wall intersects
            x_min_grid = int(max(0, x_min / self.width * grid_size))
            x_max_grid = int(min(grid_size - 1, x_max / self.width * grid_size))
            y_min_grid = int(max(0, y_min / self.height * grid_size))
            y_max_grid = int(min(grid_size - 1, y_max / self.height * grid_size))

            # Add wall index to all intersecting grid cells
            for x_grid in range(x_min_grid, x_max_grid + 1):
                for y_grid in range(y_min_grid, y_max_grid + 1):
                    grid_key = (x_grid, y_grid)
                    if grid_key not in self.wall_grid:
                        self.wall_grid[grid_key] = set()
                    self.wall_grid[grid_key].add(wall_idx)

        # Also create the optimized wall distance grid
        self.wall_distance_grid = [[float('inf') for _ in range(grid_size)] for _ in range(grid_size)]

        # Calculate distances for each grid cell
        cell_width = self.width / grid_size
        cell_height = self.height / grid_size

        for i in range(grid_size):
            for j in range(grid_size):
                # Cell center coordinates
                cell_x = (i + 0.5) * cell_width
                cell_y = (j + 0.5) * cell_height

                # Find minimum distance to any wall
                min_dist = float('inf')
                for wall in self.walls:
                    x_min, y_min, x_max, y_max = wall

                    # Calculate distance to wall
                    if x_min <= cell_x <= x_max and y_min <= cell_y <= y_max:
                        dist = 0
                    else:
                        # Calculate distance to closest point on wall
                        dx = max(x_min - cell_x, 0, cell_x - x_max)
                        dy = max(y_min - cell_y, 0, cell_y - y_max)
                        dist = math.sqrt(dx * dx + dy * dy)

                    min_dist = min(min_dist, dist)

                self.wall_distance_grid[i][j] = min_dist

    def _create_all_agents(self):
        """Create all agents at once with more efficient initialization"""
        # Choose shooter index in advance
        shooter_index = random.randint(0, self.num_students - 1) if self.num_students > 0 else -1

        # Generate reasonably spaced positions
        positions = self._generate_agent_positions(self.num_students + self.num_adults)

        # Create all agents using the factory
        for i in range(self.num_students):
            is_shooter = (i == shooter_index)
            agent = AgentFactory.create_agent("student", i, self, positions[i], is_shooter)
            self.schedule.append(agent)
            self.spatial_grid.update_agent(agent)

        # Create adult agents
        for i in range(self.num_adults):
            agent = AgentFactory.create_agent("adult", i + self.num_students, self,
                                              positions[i + self.num_students])
            self.schedule.append(agent)
            self.spatial_grid.update_agent(agent)

    def _generate_agent_positions(self, count):
        """Generate reasonably spaced initial positions for agents"""
        positions = []
        min_spacing = 8.0  # Minimum distance between agents
        max_attempts = 100  # Max attempts to place each agent

        for _ in range(count):
            for attempt in range(max_attempts):
                x = random.uniform(10, self.width - 10)
                y = random.uniform(10, self.height - 10)
                candidate = (x, y)

                # Check if too close to existing positions
                if all(math.hypot(x - px, y - py) >= min_spacing for px, py in positions):
                    positions.append(candidate)
                    break

                if attempt == max_attempts - 1:
                    # Last resort - just add a position
                    positions.append((random.uniform(5, self.width - 5),
                                      random.uniform(5, self.height - 5)))

        return positions

    def step_continuous(self, dt):
        """Optimized continuous time step with single spatial grid update"""
        # Update the total simulation time
        self.simulation_time += dt

        # Activate all agents in random order
        random.shuffle(self.schedule)
        for agent in self.schedule:
            agent.step_continuous(dt)

        # No need for a second spatial grid update - agents update it when they move

    def remove_agent(self, agent):
        """Remove an agent with proper cleanup"""
        if agent in self.schedule:
            # Remove from spatial grid first
            self.spatial_grid.remove_agent(agent)
            # Then remove from schedule
            self.schedule.remove(agent)