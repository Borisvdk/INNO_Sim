import random
import math


class SchoolAgent:
    """Basis agent klasse voor alle agenten in de school simulatie."""

    def __init__(self, unique_id, model, agent_type, position, agents):
        self.unique_id = unique_id
        self.model = model
        self.agent_type = agent_type  # STUDENT of ADULT
        self.position = position
        self.has_weapon = False
        self.awareness = 0.0
        self.agents = agents

        # Aangepaste snelheid voor grotere school
        self.max_speed = 100.0

        # Agent physical properties
        self.radius = 3.0  # Agent radius in world units
        self.mass = 1.0
        if agent_type == "adult":
            self.radius = 4.0  # Adults slightly larger
            self.mass = 1.3

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

        if agent_type == "adult":  # ADULT
            self.idle_prob = 0.7
            self.idle_duration = random.uniform(1.5, 4)
            self.path_time = random.uniform(1, 3)

        # **Proximity check timer**
        self.proximity_timer = 0.0  # Keeps track of time since last check
        self.proximity_check_interval = 1

        # Collision avoidance parameters
        self.personal_space = self.radius * 1.5  # Agents begin avoiding when closer than this
        self.min_distance = self.radius  # Minimum distance between agent centers
        self.avoidance_strength = 30.0  # How strongly agents avoid each other
        self.wall_avoidance_strength = 50.0  # How strongly agents avoid walls

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
        """Calculate repulsive forces from nearby agents"""
        force_x, force_y = 0, 0

        for agent in self.agents:
            if agent != self:
                dist = self.distance_to(agent)

                # Only apply force if within personal space but not overlapping
                if dist < self.personal_space and dist > 0:
                    # Calculate direction vector from other agent to this agent
                    dx = self.position[0] - agent.position[0]
                    dy = self.position[1] - agent.position[1]

                    # Normalize direction vector
                    magnitude = math.sqrt(dx * dx + dy * dy)
                    if magnitude > 0:
                        dx /= magnitude
                        dy /= magnitude

                    # Force is stronger as agents get closer
                    # Inverse square law: force ∝ 1/distance²
                    force_strength = self.avoidance_strength / (dist * dist)

                    # Add to total force
                    force_x += dx * force_strength
                    force_y += dy * force_strength

        return force_x, force_y

    def calculate_wall_avoidance(self):
        """Calculate repulsive forces from walls"""
        force_x, force_y = 0, 0
        margin = self.radius * 3  # How close to wall before avoidance kicks in

        # Avoid walls
        for wall in self.model.walls:
            x_min, y_min, x_max, y_max = wall

            # Check if agent is near this wall
            near_x_min = abs(self.position[0] - x_min) < margin
            near_x_max = abs(self.position[0] - x_max) < margin
            near_y_min = abs(self.position[1] - y_min) < margin
            near_y_max = abs(self.position[1] - y_max) < margin

            # Calculate distances to each wall
            dist_x_min = self.position[0] - x_min
            dist_x_max = x_max - self.position[0]
            dist_y_min = self.position[1] - y_min
            dist_y_max = y_max - self.position[1]

            # Apply forces based on proximity to walls
            if near_x_min and self.position[1] >= y_min and self.position[1] <= y_max:
                force_x += self.wall_avoidance_strength / (dist_x_min + 0.1)

            if near_x_max and self.position[1] >= y_min and self.position[1] <= y_max:
                force_x -= self.wall_avoidance_strength / (dist_x_max + 0.1)

            if near_y_min and self.position[0] >= x_min and self.position[0] <= x_max:
                force_y += self.wall_avoidance_strength / (dist_y_min + 0.1)

            if near_y_max and self.position[0] >= x_min and self.position[0] <= x_max:
                force_y -= self.wall_avoidance_strength / (dist_y_max + 0.1)

        return force_x, force_y

    def would_collide(self, proposed_position):
        """Check if moving to proposed_position would cause collision with any agent"""
        for agent in self.agents:
            if agent != self:
                dist = math.sqrt((proposed_position[0] - agent.position[0]) ** 2 +
                                 (proposed_position[1] - agent.position[1]) ** 2)
                if dist < (self.radius + agent.radius):
                    return True
        return False

    def distance_to(self, other_agent):
        """Calculate distance to another agent"""
        return math.sqrt((self.position[0] - other_agent.position[0]) ** 2 +
                         (self.position[1] - other_agent.position[1]) ** 2)

    def check_proximity(self, radius):
        """Check which agents are within a given radius of each other"""
        for agent in self.agents:
            for other in self.agents:
                if agent != other:
                    dist = agent.distance_to(other)
                    if dist <= radius:
                        pass
                        # print(f"{agent.unique_id} is within {radius} of {other.unique_id} (dist={dist:.2f})")

    def step_continuous(self, dt):
        """Voer de acties uit voor een continue tijdstap met delta tijd dt."""
        self.move_continuous(dt)

        # **Only check proximity if enough time has passed**
        self.proximity_timer += dt
        if self.proximity_timer >= self.proximity_check_interval:
            self.check_proximity(5)
            self.proximity_timer = 0  # Reset timer