import random
import math
from utilities import has_line_of_sight
import config
import pygame


class SchoolAgent:
    """Base agent class for all agents in the school simulation."""

    def __init__(self, unique_id, model, agent_type, position):
        """
        Initialize a base SchoolAgent.

        Args:
            unique_id: A unique identifier for the agent.
            model: The model instance the agent belongs to.
            agent_type: The type of agent ("student" or "adult").
            position: The initial (x, y) position of the agent.
        """
        self.unique_id = unique_id
        self.model = model
        self.agent_type = agent_type
        self.position = position
        self.has_weapon = False
        self.awareness = 0.0

        if agent_type == "adult":
            self.radius = config.ADULT_RADIUS
            self.mass = config.ADULT_MASS
            self.max_speed = config.ADULT_MAX_SPEED
            self.idle_prob = config.ADULT_IDLE_PROBABILITY
            self.idle_duration = random.uniform(*config.ADULT_IDLE_DURATION_RANGE)
            self.path_time = random.uniform(*config.ADULT_PATH_TIME_RANGE)
            self.response_delay = random.uniform(*config.ADULT_RESPONSE_DELAY_RANGE)
        else:
            self.radius = config.STUDENT_RADIUS
            self.mass = config.STUDENT_MASS
            self.max_speed = config.STUDENT_MAX_SPEED
            self.idle_prob = config.STUDENT_IDLE_PROBABILITY
            self.idle_duration = random.uniform(*config.STUDENT_IDLE_DURATION_RANGE)
            self.path_time = random.uniform(*config.STUDENT_PATH_TIME_RANGE)

        self.velocity = (0.0, 0.0)
        self.direction = random.uniform(0, 2 * math.pi)
        self.target_speed = random.uniform(0.75 * self.max_speed, self.max_speed)
        self.acceleration = 0.8

        self.current_path_time = 0
        self.is_idle = False
        self.idle_time = 0

        self.personal_space = self.radius * 3
        self.min_distance = self.radius * 2
        self.avoidance_strength = config.AVOIDANCE_STRENGTH
        self.wall_avoidance_strength = config.WALL_AVOIDANCE_STRENGTH
        self.wall_avoidance_margin = self.radius * 10.0

        self.personal_space_squared = self.personal_space ** 2
        self.min_distance_squared = self.min_distance ** 2

        self.last_wall_collision_vector = None

    def get_forces_and_collisions(self, proposed_position=None):
        """
        Calculate agent-agent avoidance forces and check for collisions at a given position.

        Args:
            proposed_position (tuple, optional): The position to check forces/collisions at.
                                                 If None, uses the agent's current position. Defaults to None.

        Returns:
            tuple: (force_x, force_y, would_collide) where forces are avoidance forces
                   and would_collide is True if a collision would occur at the proposed position.
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
                    if dist_squared > 1e-6:
                        dist = math.sqrt(dist_squared)
                        overlap = combined_radii - dist
                        push_force = self.avoidance_strength * overlap * 15
                        force_x += (dx / dist) * push_force
                        force_y += (dy / dist) * push_force
                    else:
                        force_x += random.uniform(-1, 1) * self.avoidance_strength * 10
                        force_y += random.uniform(-1, 1) * self.avoidance_strength * 10

                elif dist_squared < personal_space_sq and dist_squared > 1e-6:
                    dist = math.sqrt(dist_squared)
                    force_strength = self.avoidance_strength * (self.personal_space / dist - 1.0) ** 2

                    norm_dx = dx / dist
                    norm_dy = dy / dist

                    force_x += norm_dx * force_strength
                    force_y += norm_dy * force_strength

        return force_x, force_y, would_collide

    def calculate_wall_avoidance(self):
        """
        Calculate forces to avoid walls (boundary and internal).

        Returns:
            tuple: (force_x, force_y) representing the wall avoidance force vector.
        """
        force_x, force_y = 0, 0
        pos_x, pos_y = self.position
        margin = self.wall_avoidance_margin
        margin_sq = margin * margin

        if pos_x < margin:
            dist = pos_x
            force = self.wall_avoidance_strength * (margin / max(dist, 1e-4)) ** 1.5
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

        for wall_rect in self.model.walls:
            closest_x = max(wall_rect.left, min(pos_x, wall_rect.right))
            closest_y = max(wall_rect.top, min(pos_y, wall_rect.bottom))

            dx = pos_x - closest_x
            dy = pos_y - closest_y
            dist_squared = dx * dx + dy * dy

            if 0 < dist_squared < margin_sq:
                dist = math.sqrt(dist_squared)
                force_strength = self.wall_avoidance_strength * (margin / dist - 1.0) ** 2

                norm_dx = dx / dist
                norm_dy = dy / dist

                force_x += norm_dx * force_strength
                force_y += norm_dy * force_strength
                self.last_wall_collision_vector = pygame.Vector2(norm_dx, norm_dy)

        return force_x, force_y

    def would_collide_with_wall(self, position):
        """
        Check if a given position would result in a collision with a wall.

        Args:
            position (tuple): The (x, y) position to check.

        Returns:
            bool: True if the position collides with a wall, False otherwise.
        """
        x, y = position
        check_radius = self.radius * 1.5

        if not (check_radius <= x <= self.model.width - check_radius and
                check_radius <= y <= self.model.height - check_radius):
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
                                                                 random.uniform(-1, 1)).normalize()
            return True

        for wall_rect in self.model.walls:
            inflated_wall = wall_rect.inflate(check_radius * 2, check_radius * 2)
            if inflated_wall.collidepoint(x, y):
                closest_x = max(wall_rect.left, min(x, wall_rect.right))
                closest_y = max(wall_rect.top, min(y, wall_rect.bottom))
                dx = x - closest_x
                dy = y - closest_y
                dist_sq = dx * dx + dy * dy
                if dist_sq < check_radius * check_radius:
                    if dist_sq > 1e-6:
                        dist = math.sqrt(dist_sq)
                        self.last_wall_collision_vector = pygame.Vector2(dx / dist, dy / dist)
                    else:
                        self.last_wall_collision_vector = pygame.Vector2(dx,
                                                                         dy).normalize() if dx != 0 or dy != 0 else pygame.Vector2(
                            random.uniform(-1, 1), random.uniform(-1, 1)).normalize()

                    return True

        self.last_wall_collision_vector = None
        return False

    def move_continuous(self, dt):
        """
        Calculate and apply movement for the agent based on forces, target direction, and collisions.

        Args:
            dt: The time step duration.
        """
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
            self.direction += random.uniform(-math.pi / 3, math.pi / 3)
            self.direction %= (2 * math.pi)
            self.target_speed = random.uniform(0.5 * self.max_speed, self.max_speed)

            idle_threshold = self.idle_prob
            if random.random() < idle_threshold * dt:
                self.is_idle = True
                self.velocity = (0, 0)
                self.idle_time = 0
                return

        target_vx_base = self.target_speed * math.cos(self.direction)
        target_vy_base = self.target_speed * math.sin(self.direction)

        avoidance_fx, avoidance_fy, _ = self.get_forces_and_collisions()
        wall_fx, wall_fy = self.calculate_wall_avoidance()

        total_force_x = avoidance_fx * 0.5 + wall_fx * 1.5
        total_force_y = avoidance_fy * 0.5 + wall_fy * 1.5

        effective_mass = max(0.1, self.mass)
        dvx = (total_force_x / effective_mass) * dt
        dvy = (total_force_y / effective_mass) * dt

        current_vx, current_vy = self.velocity
        interim_vx = current_vx + dvx
        interim_vy = current_vy + dvy

        desired_steer_vx = target_vx_base - interim_vx
        desired_steer_vy = target_vy_base - interim_vy

        steer_accel = self.acceleration * dt * 15
        final_vx = interim_vx + desired_steer_vx * steer_accel
        final_vy = interim_vy + desired_steer_vy * steer_accel

        speed_sq = final_vx * final_vx + final_vy * final_vy
        if speed_sq > self.max_speed * self.max_speed:
            speed = math.sqrt(speed_sq)
            scale = self.max_speed / speed
            final_vx *= scale
            final_vy *= scale

        self.velocity = (final_vx, final_vy)

        step_vx, step_vy = self.velocity
        potential_x = self.position[0] + step_vx * dt
        potential_y = self.position[1] + step_vy * dt

        potential_pos = (potential_x, potential_y)

        wall_collision = self.would_collide_with_wall(potential_pos)

        final_pos = potential_pos
        if wall_collision and self.last_wall_collision_vector:
            vel_vec = pygame.Vector2(self.velocity)
            wall_normal = self.last_wall_collision_vector.normalize()

            vel_dot_normal = vel_vec.dot(wall_normal)

            if vel_dot_normal < 0:
                vel_into_wall = wall_normal * vel_dot_normal
                vel_tangential = vel_vec - vel_into_wall

                bounce_factor = 0.1
                vel_bounce = wall_normal * abs(vel_dot_normal) * bounce_factor

                self.velocity = (vel_tangential.x + vel_bounce.x, vel_tangential.y + vel_bounce.y)
            else:
                self.velocity = (vel_vec.x * 0.8, vel_vec.y * 0.8)

            step_vx_adj, step_vy_adj = self.velocity
            potential_x_adj = self.position[0] + step_vx_adj * dt
            potential_y_adj = self.position[1] + step_vy_adj * dt
            final_pos = (potential_x_adj, potential_y_adj)

            if self.would_collide_with_wall(final_pos):
                final_pos = self.position
                self.velocity = (0, 0)

        final_x = max(self.radius, min(final_pos[0], self.model.width - self.radius))
        final_y = max(self.radius, min(final_pos[1], self.model.height - self.radius))
        final_pos = (final_x, final_y)

        _, _, agent_collision = self.get_forces_and_collisions(final_pos)

        if agent_collision:
            final_pos = self.position
            self.velocity = (0, 0)

        if final_pos != self.position:
            self.position = final_pos
            self.model.spatial_grid.update_agent(self)

    def has_line_of_sight(self, target_position):
        """
        Check if this agent has line of sight to the target position, considering obstacles.

        Args:
            target_position (tuple): The (x, y) coordinate of the target.

        Returns:
            bool: True if line of sight exists, False otherwise.
        """
        return has_line_of_sight(self.position, target_position, self.model.vision_blocking_obstacles)

    def step_continuous(self, dt):
        """
        Default continuous step function for agents. Primarily handles movement.

        Args:
            dt: The time step duration.
        """
        self.move_continuous(dt)