import random
import math
from utilities import has_line_of_sight
import config  # Import config to potentially use parameters
import pygame  # Needed for wall collision response vector math


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
            self.radius = config.ADULT_RADIUS
            self.mass = config.ADULT_MASS
            self.max_speed = config.ADULT_MAX_SPEED
            self.idle_prob = config.ADULT_IDLE_PROBABILITY
            self.idle_duration = random.uniform(*config.ADULT_IDLE_DURATION_RANGE)
            self.path_time = random.uniform(*config.ADULT_PATH_TIME_RANGE)
            self.response_delay = random.uniform(*config.ADULT_RESPONSE_DELAY_RANGE)
        else:  # student
            self.radius = config.STUDENT_RADIUS
            self.mass = config.STUDENT_MASS
            self.max_speed = config.STUDENT_MAX_SPEED
            self.idle_prob = config.STUDENT_IDLE_PROBABILITY
            self.idle_duration = random.uniform(*config.STUDENT_IDLE_DURATION_RANGE)
            self.path_time = random.uniform(*config.STUDENT_PATH_TIME_RANGE)

        # Speed and movement parameters
        self.velocity = (0.0, 0.0)
        self.direction = random.uniform(0, 2 * math.pi)
        self.target_speed = random.uniform(0.75 * self.max_speed, self.max_speed)
        self.acceleration = 0.8  # Slightly higher acceleration

        # State variables
        self.current_path_time = 0
        self.is_idle = False
        self.idle_time = 0

        # Collision avoidance parameters (using config)
        self.personal_space = self.radius * 3
        self.min_distance = self.radius * 2
        self.avoidance_strength = config.AVOIDANCE_STRENGTH
        self.wall_avoidance_strength = config.WALL_AVOIDANCE_STRENGTH
        # Significantly increased margin for wall avoidance force calculation
        self.wall_avoidance_margin = self.radius * 10.0

        # Cached squared distances for faster computation
        self.personal_space_squared = self.personal_space ** 2
        self.min_distance_squared = self.min_distance ** 2

        # For wall collision response
        self.last_wall_collision_vector = None

    def get_forces_and_collisions(self, proposed_position=None):
        """Calculate both avoidance forces and check collisions in a single pass.
        Returns: (force_x, force_y, would_collide)
        """
        force_x, force_y = 0, 0
        would_collide = False
        check_position = proposed_position if proposed_position else self.position

        search_radius = max(self.personal_space, self.min_distance)
        nearby_agents = self.model.spatial_grid.get_nearby_agents(check_position, search_radius)

        personal_space_sq = self.personal_space_squared
        min_distance_sq = self.min_distance_squared
        check_x, check_y = check_position

        for agent in nearby_agents:
            if agent != self and agent in self.model.schedule:
                agent_x, agent_y = agent.position
                dx = check_x - agent_x
                dy = check_y - agent_y
                dist_squared = dx * dx + dy * dy

                combined_radii = self.radius + agent.radius
                combined_radii_sq = combined_radii * combined_radii

                if proposed_position and dist_squared < combined_radii_sq:
                    would_collide = True
                    # Apply strong push if colliding in proposed position
                    if dist_squared > 1e-6:
                        dist = math.sqrt(dist_squared)
                        overlap = combined_radii - dist
                        push_force = self.avoidance_strength * overlap * 15  # Even stronger push
                        force_x += (dx / dist) * push_force
                        force_y += (dy / dist) * push_force
                    else:  # Overlapping exactly
                        force_x += random.uniform(-1, 1) * self.avoidance_strength * 10
                        force_y += random.uniform(-1, 1) * self.avoidance_strength * 10

                elif dist_squared < personal_space_sq and dist_squared > 1e-6:
                    dist = math.sqrt(dist_squared)
                    # Force calculation that increases more sharply closer up
                    force_strength = self.avoidance_strength * (self.personal_space / dist - 1.0) ** 2

                    norm_dx = dx / dist
                    norm_dy = dy / dist

                    force_x += norm_dx * force_strength
                    force_y += norm_dy * force_strength

        return force_x, force_y, would_collide

    def calculate_wall_avoidance(self):
        """Stronger wall avoidance force calculation with steeper falloff."""
        force_x, force_y = 0, 0
        pos_x, pos_y = self.position
        margin = self.wall_avoidance_margin
        margin_sq = margin * margin

        # Check boundary walls
        if pos_x < margin:
            dist = pos_x
            force = self.wall_avoidance_strength * (margin / max(dist, 1e-4)) ** 1.5  # Steeper falloff
            force_x += force
        elif pos_x > self.model.width - margin:
            dist = self.model.width - pos_x
            force = self.wall_avoidance_strength * (margin / max(dist, 1e-4)) ** 1.5
            force_x -= force

        if pos_y < margin:
            dist = pos_y
            force = self.wall_avoidance_strength * (margin / max(dist, 1e-4)) ** 1.5
            force_y += force
        elif pos_y > self.model.height - margin:
            dist = self.model.height - pos_y
            force = self.wall_avoidance_strength * (margin / max(dist, 1e-4)) ** 1.5
            force_y -= force

        # Check internal walls
        for wall_rect in self.model.walls:
            closest_x = max(wall_rect.left, min(pos_x, wall_rect.right))
            closest_y = max(wall_rect.top, min(pos_y, wall_rect.bottom))

            dx = pos_x - closest_x
            dy = pos_y - closest_y
            dist_squared = dx * dx + dy * dy

            if 0 < dist_squared < margin_sq:
                dist = math.sqrt(dist_squared)
                # Steeper force increase closer to the wall
                force_strength = self.wall_avoidance_strength * (margin / dist - 1.0) ** 2

                norm_dx = dx / dist
                norm_dy = dy / dist

                force_x += norm_dx * force_strength
                force_y += norm_dy * force_strength
                # Store collision normal for potential use in collision response
                self.last_wall_collision_vector = pygame.Vector2(norm_dx, norm_dy)

        return force_x, force_y

    def would_collide_with_wall(self, position):
        """Check if a position would collide with any wall, using a larger buffer."""
        x, y = position
        # Increased buffer significantly to encourage staying away
        check_radius = self.radius * 1.5

        if not (check_radius <= x <= self.model.width - check_radius and
                check_radius <= y <= self.model.height - check_radius):
            # Determine normal vector for boundary collision
            if x < check_radius:
                self.last_wall_collision_vector = pygame.Vector2(1, 0)
            elif x > self.model.width - check_radius:
                self.last_wall_collision_vector = pygame.Vector2(-1, 0)
            elif y < check_radius:
                self.last_wall_collision_vector = pygame.Vector2(0, 1)
            elif y > self.model.height - check_radius:
                self.last_wall_collision_vector = pygame.Vector2(0, -1)
            else:
                self.last_wall_collision_vector = pygame.Vector2(random.uniform(-1, 1),
                                                                 random.uniform(-1, 1)).normalize()  # Fallback
            return True

        for wall_rect in self.model.walls:
            # Use inflate based on check_radius
            inflated_wall = wall_rect.inflate(check_radius * 2, check_radius * 2)
            if inflated_wall.collidepoint(x, y):
                # Calculate distance to the *original* wall rectangle's closest point
                closest_x = max(wall_rect.left, min(x, wall_rect.right))
                closest_y = max(wall_rect.top, min(y, wall_rect.bottom))
                dx = x - closest_x
                dy = y - closest_y
                dist_sq = dx * dx + dy * dy
                if dist_sq < check_radius * check_radius:
                    # Store the normal vector pointing away from the wall
                    if dist_sq > 1e-6:
                        dist = math.sqrt(dist_sq)
                        self.last_wall_collision_vector = pygame.Vector2(dx / dist, dy / dist)
                    else:  # Exactly on the point, guess normal based on closest edge
                        # This part is complex to get right, using a simple push might be better
                        self.last_wall_collision_vector = pygame.Vector2(dx,
                                                                         dy).normalize() if dx != 0 or dy != 0 else pygame.Vector2(
                            random.uniform(-1, 1), random.uniform(-1, 1)).normalize()

                    return True  # Collision confirmed

        self.last_wall_collision_vector = None  # No collision
        return False

    def move_continuous(self, dt):
        """Movement logic with stronger wall avoidance and better collision response."""
        if self.is_idle:
            self.idle_time += dt
            if self.idle_time >= self.idle_duration:
                self.is_idle = False
                self.direction = random.uniform(0, 2 * math.pi)
                self.target_speed = random.uniform(0.5 * self.max_speed, self.max_speed)
                self.current_path_time = 0
                self.idle_duration = random.uniform(
                    *config.ADULT_IDLE_DURATION_RANGE) if self.agent_type == "adult" else random.uniform(
                    *config.STUDENT_IDLE_DURATION_RANGE)
            else:
                self.velocity = (0, 0)
                return

        self.current_path_time += dt
        if self.current_path_time >= self.path_time:
            self.current_path_time = 0
            self.path_time = random.uniform(
                *config.ADULT_PATH_TIME_RANGE) if self.agent_type == "adult" else random.uniform(
                *config.STUDENT_PATH_TIME_RANGE)
            self.direction += random.uniform(-math.pi / 3, math.pi / 3)  # Moderate direction change
            self.direction %= (2 * math.pi)
            self.target_speed = random.uniform(0.5 * self.max_speed, self.max_speed)

            idle_threshold = self.idle_prob
            if random.random() < idle_threshold * dt:
                self.is_idle = True
                self.velocity = (0, 0)
                self.idle_time = 0
                return

        # --- Force Calculation ---
        target_vx_base = self.target_speed * math.cos(self.direction)
        target_vy_base = self.target_speed * math.sin(self.direction)

        avoidance_fx, avoidance_fy, _ = self.get_forces_and_collisions()
        wall_fx, wall_fy = self.calculate_wall_avoidance()

        # Give wall avoidance very high priority
        total_force_x = avoidance_fx * 0.5 + wall_fx * 1.5
        total_force_y = avoidance_fy * 0.5 + wall_fy * 1.5

        effective_mass = max(0.1, self.mass)
        # Forces directly modify acceleration (dv = F/m * dt)
        dvx = (total_force_x / effective_mass) * dt
        dvy = (total_force_y / effective_mass) * dt

        # --- Velocity Update ---
        # Apply acceleration from forces first
        current_vx, current_vy = self.velocity
        interim_vx = current_vx + dvx
        interim_vy = current_vy + dvy

        # Then, steer towards the base target velocity (direction goal)
        # Calculate desired velocity change towards the base target
        desired_steer_vx = target_vx_base - interim_vx
        desired_steer_vy = target_vy_base - interim_vy

        # Apply steering acceleration
        steer_accel = self.acceleration * dt * 15  # Stronger steering towards goal when not avoiding
        final_vx = interim_vx + desired_steer_vx * steer_accel
        final_vy = interim_vy + desired_steer_vy * steer_accel

        # Speed Limiting
        speed_sq = final_vx * final_vx + final_vy * final_vy
        if speed_sq > self.max_speed * self.max_speed:
            speed = math.sqrt(speed_sq)
            scale = self.max_speed / speed
            final_vx *= scale
            final_vy *= scale

        self.velocity = (final_vx, final_vy)

        # --- Position Update and Collision Handling ---
        step_vx, step_vy = self.velocity
        potential_x = self.position[0] + step_vx * dt
        potential_y = self.position[1] + step_vy * dt

        potential_pos = (potential_x, potential_y)

        wall_collision = self.would_collide_with_wall(potential_pos)

        final_pos = potential_pos
        if wall_collision and self.last_wall_collision_vector:
            # Wall collision response: Stop movement *into* the wall, allow tangential.
            # Project velocity onto the tangent of the wall normal.
            vel_vec = pygame.Vector2(self.velocity)
            wall_normal = self.last_wall_collision_vector.normalize()

            # Velocity component parallel to the wall normal (into the wall)
            vel_dot_normal = vel_vec.dot(wall_normal)

            # If moving into the wall, remove that component
            if vel_dot_normal < 0:
                vel_into_wall = wall_normal * vel_dot_normal
                vel_tangential = vel_vec - vel_into_wall

                # Apply a slight bounce away from the wall
                bounce_factor = 0.1  # Small bounce
                vel_bounce = wall_normal * abs(vel_dot_normal) * bounce_factor

                # New velocity is tangential plus bounce
                self.velocity = (vel_tangential.x + vel_bounce.x, vel_tangential.y + vel_bounce.y)
            else:
                # Moving away or parallel, allow it but maybe reduce speed
                self.velocity = (vel_vec.x * 0.8, vel_vec.y * 0.8)

            # Recalculate potential position based on adjusted velocity after collision response
            step_vx_adj, step_vy_adj = self.velocity
            potential_x_adj = self.position[0] + step_vx_adj * dt
            potential_y_adj = self.position[1] + step_vy_adj * dt
            final_pos = (potential_x_adj, potential_y_adj)

            # Final safety check after adjustment
            if self.would_collide_with_wall(final_pos):
                final_pos = self.position  # If still colliding, don't move
                self.velocity = (0, 0)

        # Clamp final position to bounds (redundant if would_collide_with_wall handles boundaries)
        final_x = max(self.radius, min(final_pos[0], self.model.width - self.radius))
        final_y = max(self.radius, min(final_pos[1], self.model.height - self.radius))
        final_pos = (final_x, final_y)

        # Check for agent collisions at the final position
        _, _, agent_collision = self.get_forces_and_collisions(final_pos)

        if agent_collision:
            # Agent collision: Stop movement for this step
            final_pos = self.position
            self.velocity = (0, 0)

        # Update position and spatial grid if moved
        if final_pos != self.position:
            self.position = final_pos
            self.model.spatial_grid.update_agent(self)

    def has_line_of_sight(self, target_position):
        """
        Check if this agent has line of sight to the target position.
        Uses the utility function with the model's combined obstacles.
        """
        return has_line_of_sight(self.position, target_position, self.model.vision_blocking_obstacles)

    def step_continuous(self, dt):
        """Default step function for agents (usually overridden)."""
        self.move_continuous(dt)