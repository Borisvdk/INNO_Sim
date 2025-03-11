import random
import math


class SpatialGrid:
    """A grid-based spatial partitioning system for efficiently finding nearby agents."""

    def __init__(self, width, height, cell_size):
        self.cell_size = cell_size
        self.grid_width = math.ceil(width / cell_size)
        self.grid_height = math.ceil(height / cell_size)
        self.grid = {}  # Dictionary of {(cell_x, cell_y): [agents]}

    def clear(self):
        """Clear all cells in the grid."""
        self.grid = {}

    def add_agent(self, agent):
        """Add an agent to the appropriate grid cell."""
        cell_x, cell_y = self._get_cell_indices(agent.position)
        cell_key = (cell_x, cell_y)

        if cell_key not in self.grid:
            self.grid[cell_key] = []

        self.grid[cell_key].append(agent)

    def _get_cell_indices(self, position):
        """Convert a position to grid cell indices."""
        x, y = position
        cell_x = int(x / self.cell_size)
        cell_y = int(y / self.cell_size)
        return cell_x, cell_y

    def get_nearby_agents(self, position, radius):
        """Get all agents within a certain radius of a position."""
        center_x, center_y = position
        # Calculate the cell range that could contain agents within the radius
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


class SchoolAgent:
    """Basis agent klasse voor alle agenten in de school simulatie."""

    def __init__(self, unique_id, model, agent_type, position, agents):
        self.unique_id = unique_id
        self.model = model
        self.agent_type = agent_type  # STUDENT of ADULT
        self.position = position
        self.has_weapon = False
        self.awareness = 0.0
        self.agents = agents  # We'll keep this for backward compatibility, but won't use it for proximity

        # Agent physical properties
        self.radius = 3.0  # Agent radius in world units
        self.mass = 1.0
        if agent_type == "adult":
            self.radius = 4.0  # Adults slightly larger
            self.mass = 1.3

        # Aangepaste snelheid voor grotere school
        self.max_speed = 100.0

        # Parameters voor menselijkere beweging
        self.velocity = (0.0, 0.0)
        self.direction = random.uniform(0, 2 * math.pi)  # Richting in radialen
        self.target_speed = random.uniform(0.75 * self.max_speed, self.max_speed)  # Doelsnelheid
        self.acceleration = 0.5  # Hoe snel agent versnelt/vertraagt

        # Richtingsverandering & stilstand parameters
        self.path_time = random.uniform(0.5, 2)
        self.current_path_time = 0
        self.is_idle = False
        self.idle_prob = 0.5
        self.idle_time = 0
        self.idle_duration = random.uniform(1, 3)

        if agent_type == "adult":
            self.idle_prob = 0.7
            self.idle_duration = random.uniform(1.5, 4)
            self.path_time = random.uniform(1, 3)

        # Collision avoidance parameters
        self.personal_space = self.radius * 3  # Agents begin avoiding when closer than this
        self.min_distance = self.radius * 2  # Minimum distance between agent centers
        self.avoidance_strength = 30.0  # How strongly agents avoid each other
        self.wall_avoidance_strength = 50.0  # How strongly agents avoid walls

        # Optimize by caching square of distances to avoid square root calculations
        self.personal_space_squared = self.personal_space ** 2
        self.min_distance_squared = self.min_distance ** 2

    def move_continuous(self, dt):
        """Beweeg de agent volgens huidige richting en snelheid met delta tijd."""
        if self.is_idle:
            self.idle_time += dt
            if self.idle_time >= self.idle_duration:
                self.is_idle = False
                self.direction = random.uniform(0, 2 * math.pi)
                self.target_speed = random.uniform(0.5, self.max_speed)
                self.current_path_time = 0
            return

        self.current_path_time += dt
        if self.current_path_time >= self.path_time:
            self.current_path_time = 0
            self.path_time = random.uniform(0.5, 2)
            if self.agent_type == "adult":
                self.path_time = random.uniform(1, 3)

            self.direction += random.uniform(-math.pi, math.pi)
            self.direction %= 2 * math.pi
            self.target_speed = random.uniform(0.5, self.max_speed)

            if random.random() < self.idle_prob:
                self.is_idle = True
                self.velocity = (0, 0)
                self.idle_time = 0
                self.idle_duration = random.uniform(1, 3)
                if self.agent_type == "adult":
                    self.idle_duration = random.uniform(1.5, 4)
                return

        # Calculate target velocity based on desired direction and speed
        target_vx = self.target_speed * math.cos(self.direction)
        target_vy = self.target_speed * math.sin(self.direction)

        # Calculate avoidance forces from other agents
        avoidance_fx, avoidance_fy = self.calculate_avoidance_forces()

        # Calculate wall avoidance forces
        wall_fx, wall_fy = self.calculate_wall_avoidance()

        # Combine all forces
        total_fx = avoidance_fx + wall_fx
        total_fy = avoidance_fy + wall_fy

        # Apply forces to adjust target velocity
        target_vx += total_fx / self.mass
        target_vy += total_fy / self.mass

        # Apply acceleration to current velocity towards target
        current_vx, current_vy = self.velocity
        new_vx = current_vx + (target_vx - current_vx) * self.acceleration * dt * 5
        new_vy = current_vy + (target_vy - current_vy) * self.acceleration * dt * 5

        self.velocity = (new_vx, new_vy)

        # Update position
        new_x = self.position[0] + new_vx * dt
        new_y = self.position[1] + new_vy * dt

        # Handle boundary conditions
        if self.agent_type == "student":
            if new_x < 0 or new_x > self.model.width or new_y < 0 or new_y > self.model.height:
                self.model.remove_agent(self)
                return
        else:
            new_x = max(self.radius, min(new_x, self.model.width - self.radius))
            new_y = max(self.radius, min(new_y, self.model.height - self.radius))

        # Check if new position would cause collisions
        proposed_position = (new_x, new_y)
        if not self.would_collide(proposed_position):
            self.position = proposed_position
        else:
            # If collision would occur, try a reduced movement
            reduced_x = self.position[0] + (new_x - self.position[0]) * 0.5
            reduced_y = self.position[1] + (new_y - self.position[1]) * 0.5
            reduced_position = (reduced_x, reduced_y)

            if not self.would_collide(reduced_position):
                self.position = reduced_position
            # If even reduced movement causes collision, don't move

    def calculate_avoidance_forces(self):
        """Calculate repulsive forces from nearby agents using spatial grid for efficiency"""
        force_x, force_y = 0, 0

        # Get nearby agents from spatial grid instead of checking all agents
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, self.personal_space)

        for agent in nearby_agents:
            if agent != self:
                # Calculate squared distance (faster than actual distance)
                dx = self.position[0] - agent.position[0]
                dy = self.position[1] - agent.position[1]
                dist_squared = dx * dx + dy * dy

                # Only apply force if within personal space but not overlapping
                if dist_squared < self.personal_space_squared and dist_squared > 0:
                    # Force is stronger as agents get closer
                    # We can use squared distance to avoid square root
                    force_strength = self.avoidance_strength / dist_squared

                    # Normalize direction vector without square root
                    inv_dist = 1.0 / math.sqrt(dist_squared)  # Only one sqrt operation
                    norm_dx = dx * inv_dist
                    norm_dy = dy * inv_dist

                    # Add to total force
                    force_x += norm_dx * force_strength
                    force_y += norm_dy * force_strength

        return force_x, force_y

    def calculate_wall_avoidance(self):
        """Calculate repulsive forces from walls"""
        force_x, force_y = 0, 0
        margin = self.radius * 3  # How close to wall before avoidance kicks in

        # Cache position for multiple accesses
        pos_x, pos_y = self.position

        # Avoid walls - only check nearby walls instead of all walls
        x_min_grid = int(max(0, (pos_x - margin) / self.model.width * 10))
        x_max_grid = int(min(9, (pos_x + margin) / self.model.width * 10))
        y_min_grid = int(max(0, (pos_y - margin) / self.model.height * 10))
        y_max_grid = int(min(9, (pos_y + margin) / self.model.height * 10))

        # Get wall indices that could be nearby
        potential_wall_indices = set()
        for x_grid in range(x_min_grid, x_max_grid + 1):
            for y_grid in range(y_min_grid, y_max_grid + 1):
                grid_key = (x_grid, y_grid)
                if grid_key in self.model.wall_grid:
                    potential_wall_indices.update(self.model.wall_grid[grid_key])

        # Now only check those walls
        for wall_idx in potential_wall_indices:
            wall = self.model.walls[wall_idx]
            x_min, y_min, x_max, y_max = wall

            # Calculate distances to each wall segment
            dist_x_min = pos_x - x_min
            dist_x_max = x_max - pos_x
            dist_y_min = pos_y - y_min
            dist_y_max = y_max - pos_y

            # Apply forces based on proximity to walls - only if close enough
            if dist_x_min < margin and pos_y >= y_min and pos_y <= y_max:
                force_x += self.wall_avoidance_strength / (dist_x_min + 0.1)

            if dist_x_max < margin and pos_y >= y_min and pos_y <= y_max:
                force_x -= self.wall_avoidance_strength / (dist_x_max + 0.1)

            if dist_y_min < margin and pos_x >= x_min and pos_x <= x_max:
                force_y += self.wall_avoidance_strength / (dist_y_min + 0.1)

            if dist_y_max < margin and pos_x >= x_min and pos_x <= x_max:
                force_y -= self.wall_avoidance_strength / (dist_y_max + 0.1)

        return force_x, force_y

    def would_collide(self, proposed_position):
        """Check if moving to proposed_position would cause collision with any agent"""
        # Use spatial grid to only check nearby agents
        nearby_agents = self.model.spatial_grid.get_nearby_agents(proposed_position, self.min_distance)

        min_dist_squared = self.min_distance_squared  # Cache for speed
        prop_x, prop_y = proposed_position

        for agent in nearby_agents:
            if agent != self:
                # Calculate squared distance (faster than actual distance)
                agent_x, agent_y = agent.position
                dx = prop_x - agent_x
                dy = prop_y - agent_y
                dist_squared = dx * dx + dy * dy

                # Compare squares to avoid square root
                if dist_squared < min_dist_squared:
                    return True
        return False

    def distance_to_squared(self, other_agent):
        """Calculate squared distance to another agent (faster than actual distance)"""
        dx = self.position[0] - other_agent.position[0]
        dy = self.position[1] - other_agent.position[1]
        return dx * dx + dy * dy

    def step_continuous(self, dt):
        """Voer de acties uit voor een continue tijdstap met delta tijd dt."""
        self.move_continuous(dt)