import random
import math
from utilities import has_line_of_sight


class SchoolAgent:
    """Base agent class for all agents in the school simulation."""

    def __init__(self, unique_id, model, agent_type, position):
        self.unique_id = unique_id
        self.model = model
        self.agent_type = agent_type  # "student" or "adult"
        self.position = position
        self.has_weapon = False
        self.awareness = 0.0

        # Agent physical properties - set based on type
        if agent_type == "adult":
            self.radius = 4.0
            self.mass = 1.3
            self.idle_prob = 0.7
            self.idle_duration = random.uniform(1.5, 4)
            self.path_time = random.uniform(1, 3)
            self.response_delay = random.randint(2, 5)  # Adult-specific
        else:  # student
            self.radius = 3.0
            self.mass = 1.0
            self.idle_prob = 0.5
            self.idle_duration = random.uniform(1, 3)
            self.path_time = random.uniform(0.5, 2)

        # Speed and movement parameters
        self.max_speed = 100.0
        self.velocity = (0.0, 0.0)
        self.direction = random.uniform(0, 2 * math.pi)
        self.target_speed = random.uniform(0.75 * self.max_speed, self.max_speed)
        self.acceleration = 0.5

        # State variables
        self.current_path_time = 0
        self.is_idle = False
        self.idle_time = 0

        # Collision avoidance parameters
        self.personal_space = self.radius * 3
        self.min_distance = self.radius * 2
        self.avoidance_strength = 30.0
        self.wall_avoidance_strength = 50.0

        # Cached squared distances for faster computation
        self.personal_space_squared = self.personal_space ** 2
        self.min_distance_squared = self.min_distance ** 2

    def get_forces_and_collisions(self, proposed_position=None):
        """Calculate both avoidance forces and check collisions in a single pass.
        Returns: (force_x, force_y, would_collide)
        """
        force_x, force_y = 0, 0
        would_collide = False
        check_position = proposed_position if proposed_position else self.position

        # Get all nearby agents in one call - use the larger of personal_space or min_distance
        search_radius = max(self.personal_space, self.min_distance)
        nearby_agents = self.model.spatial_grid.get_nearby_agents(check_position, search_radius)

        # Cache squared values for faster computation
        personal_space_sq = self.personal_space_squared
        min_distance_sq = self.min_distance_squared
        check_x, check_y = check_position

        for agent in nearby_agents:
            if agent != self:
                # Calculate squared distance (faster than actual distance)
                agent_x, agent_y = agent.position
                dx = check_x - agent_x
                dy = check_y - agent_y
                dist_squared = dx * dx + dy * dy

                # Check for collision (only if requested)
                if proposed_position and dist_squared < min_distance_sq:
                    would_collide = True

                # Calculate avoidance force if within personal space
                if dist_squared < personal_space_sq and dist_squared > 0:
                    # Force is stronger as agents get closer
                    force_strength = self.avoidance_strength / dist_squared

                    # Only compute sqrt once
                    inv_dist = 1.0 / math.sqrt(dist_squared)
                    norm_dx = dx * inv_dist
                    norm_dy = dy * inv_dist

                    # Add to total force
                    force_x += norm_dx * force_strength
                    force_y += norm_dy * force_strength

        return force_x, force_y, would_collide

    def calculate_wall_avoidance(self):
        """Improved wall avoidance with stronger forces"""
        force_x, force_y = 0, 0
        pos_x, pos_y = self.position
        margin = self.radius * 5  # Increased margin for better wall detection

        # Check each wall directly for better accuracy
        for wall in self.model.walls:
            x_min, y_min, x_max, y_max = wall

            # Compute vector from position to closest point on wall
            closest_x = max(x_min, min(pos_x, x_max))
            closest_y = max(y_min, min(pos_y, y_max))

            # Vector from closest point to agent position
            dx = pos_x - closest_x
            dy = pos_y - closest_y

            # Distance squared
            dist_squared = dx * dx + dy * dy

            # Apply force if within margin
            if dist_squared < margin * margin and dist_squared > 0:
                dist = math.sqrt(dist_squared)

                # Stronger force when very close to wall
                if dist < self.radius * 2:
                    force_strength = self.wall_avoidance_strength * 5 / dist
                else:
                    force_strength = self.wall_avoidance_strength * 2 / dist

                # Direction away from wall
                norm_dx = dx / dist
                norm_dy = dy / dist

                force_x += norm_dx * force_strength
                force_y += norm_dy * force_strength

        return force_x, force_y

    def would_collide_with_wall(self, position):
        """Check if a position would collide with any wall"""
        x, y = position
        agent_radius = self.radius

        for wall in self.model.walls:
            wall_x1, wall_y1, wall_x2, wall_y2 = wall

            # Calculate distance to wall - treat walls as rectangles
            closest_x = max(wall_x1, min(x, wall_x2))
            closest_y = max(wall_y1, min(y, wall_y2))

            # If closest point is inside the wall, collision is certain
            if closest_x == x and closest_y == y and wall_x1 <= x <= wall_x2 and wall_y1 <= y <= wall_y2:
                return True

            # Calculate distance from agent center to closest point on wall
            dx = x - closest_x
            dy = y - closest_y
            distance_squared = dx * dx + dy * dy

            # Collision if distance is less than agent radius
            if distance_squared <= agent_radius * agent_radius:
                return True

        return False

    def move_continuous(self, dt):
        """Optimized version of agent movement with proper wall collision detection"""
        # Handle idle state
        if self.is_idle:
            self.idle_time += dt
            if self.idle_time >= self.idle_duration:
                self.is_idle = False
                self.direction = random.uniform(0, 2 * math.pi)
                self.target_speed = random.uniform(0.5, self.max_speed)
                self.current_path_time = 0
            return

        # Update path timer and possibly change direction
        self.current_path_time += dt
        if self.current_path_time >= self.path_time:
            self.current_path_time = 0
            self.path_time = random.uniform(1, 3) if self.agent_type == "adult" else random.uniform(0.5, 2)
            self.direction += random.uniform(-math.pi, math.pi)
            self.direction %= 2 * math.pi
            self.target_speed = random.uniform(0.5, self.max_speed)

            # Check for idle state transition
            idle_threshold = 0.7 if self.agent_type == "adult" else 0.5
            if random.random() < idle_threshold:
                self.is_idle = True
                self.velocity = (0, 0)
                self.idle_time = 0
                self.idle_duration = random.uniform(1.5, 4) if self.agent_type == "adult" else random.uniform(1, 3)
                return

        # Calculate target velocity
        target_vx = self.target_speed * math.cos(self.direction)
        target_vy = self.target_speed * math.sin(self.direction)

        # Get avoidance forces and collision checks in a single operation
        avoidance_fx, avoidance_fy, _ = self.get_forces_and_collisions()

        # Calculate wall avoidance forces
        wall_fx, wall_fy = self.calculate_wall_avoidance()

        # Combine all forces
        total_fx = avoidance_fx + wall_fx
        total_fy = avoidance_fy + wall_fy

        # Apply forces to adjust target velocity
        target_vx += total_fx / self.mass
        target_vy += total_fy / self.mass

        # Apply acceleration to current velocity towards target
        accel_factor = self.acceleration * dt * 5
        current_vx, current_vy = self.velocity
        new_vx = current_vx + (target_vx - current_vx) * accel_factor
        new_vy = current_vy + (target_vy - current_vy) * accel_factor

        self.velocity = (new_vx, new_vy)

        # Calculate new position
        new_x = self.position[0] + new_vx * dt
        new_y = self.position[1] + new_vy * dt

        new_x = max(self.radius, min(new_x, self.model.width - self.radius))
        new_y = max(self.radius, min(new_y, self.model.height - self.radius))

        # Check for wall collisions - this is a critical addition
        if self.would_collide_with_wall((new_x, new_y)):
            # Try reduced movement if wall collision
            reduced_x = self.position[0] + (new_x - self.position[0]) * 0.1
            reduced_y = self.position[1] + (new_y - self.position[1]) * 0.1

            if not self.would_collide_with_wall((reduced_x, reduced_y)):
                new_x, new_y = reduced_x, reduced_y
            else:
                # Can't move at all, bounce back
                self.direction = (self.direction + math.pi) % (2 * math.pi)
                self.velocity = (-self.velocity[0] * 0.5, -self.velocity[1] * 0.5)
                return

        # Check for agent collisions
        proposed_position = (new_x, new_y)
        _, _, would_collide = self.get_forces_and_collisions(proposed_position)

        if not would_collide:
            old_position = self.position
            self.position = proposed_position
            # Update spatial grid if position changed
            if old_position != self.position:
                self.model.spatial_grid.update_agent(self)
        else:
            # Try half-step if collision detected
            reduced_x = self.position[0] + (new_x - self.position[0]) * 0.5
            reduced_y = self.position[1] + (new_y - self.position[1]) * 0.5
            reduced_position = (reduced_x, reduced_y)

            if not self.would_collide_with_wall(reduced_position):
                _, _, reduced_collision = self.get_forces_and_collisions(reduced_position)

                if not reduced_collision:
                    old_position = self.position
                    self.position = reduced_position
                    if old_position != self.position:
                        self.model.spatial_grid.update_agent(self)

    def has_line_of_sight(self, target_position):
        """
        Check if this agent has line of sight to the target position.
        Returns True if there's a clear line of sight, False if a wall blocks the view.
        """
        return has_line_of_sight(self.position, target_position, self.model.walls)

    def step_continuous(self, dt):
        """Base step function for regular agents (non-shooters)"""
        self.move_continuous(dt)