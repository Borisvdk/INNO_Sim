import math
import random
from agents.schoolagent import SchoolAgent
from utilities import has_line_of_sight


class StudentAgent(SchoolAgent):
    """Agent class for students with potential shooter behaviors."""

    def __init__(self, unique_id, model, position, agent_type):
        # Initialize parent class
        super().__init__(unique_id, model, agent_type, position)

        # Student-specific attributes
        self.fear_level = 0.0
        self.grab_weapon_prob = 0.05
        self.state = "Normal"

        # Shooter-specific attributes
        self.is_shooter = False
        self.last_shot_time = 0.0
        self.shooting_interval = 2.0  # Shoot every 2 seconds
        self.shooting_range = 10.0  # Stop and shoot within 10 units
        self.hit_probability = 0.5  # 50% chance to hit

        # Search behavior tracking
        self.search_start_time = 0
        self.search_direction_change_time = 0

    def step_continuous(self, dt):
        """Override step_continuous with shooter behavior and wall awareness"""
        if not self.is_shooter:
            # Use standard movement for non-shooters
            super().step_continuous(dt)
            return

        # Shooter-specific behavior with line of sight
        current_time = self.model.simulation_time

        # Find visible target agents
        search_radius = max(self.shooting_range * 3, 100.0)  # Larger search radius to allow seeking targets
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, search_radius)

        # Filter for valid targets that are visible (not blocked by walls)
        visible_targets = []
        for agent in nearby_agents:
            if agent != self and agent.agent_type in ["student", "adult"]:
                if self.has_line_of_sight(agent.position):
                    visible_targets.append(agent)

        if not visible_targets:
            # No visible targets - move randomly to search
            self.search_behavior(dt)
        else:
            # Find nearest visible target
            nearest_agent = None
            min_distance_squared = float('inf')

            for agent in visible_targets:
                dx = self.position[0] - agent.position[0]
                dy = self.position[1] - agent.position[1]
                distance_squared = dx * dx + dy * dy

                if distance_squared < min_distance_squared:
                    min_distance_squared = distance_squared
                    nearest_agent = agent

            # Calculate actual distance only once
            distance = math.sqrt(min_distance_squared)

            if distance > self.shooting_range:
                # Move toward nearest target
                dx = nearest_agent.position[0] - self.position[0]
                dy = nearest_agent.position[1] - self.position[1]

                # Normalize direction
                inv_dist = 1.0 / distance
                direction_x = dx * inv_dist
                direction_y = dy * inv_dist

                # Set velocity directly
                self.velocity = (direction_x * self.max_speed, direction_y * self.max_speed)
            else:
                # Within shooting range - stop and attempt to shoot
                self.velocity = (0, 0)

                # Try to shoot if enough time has passed
                if current_time - self.last_shot_time >= self.shooting_interval:
                    self._shoot_at_target(nearest_agent, current_time)

        # Update position with wall collision checks
        new_x = self.position[0] + self.velocity[0] * dt
        new_y = self.position[1] + self.velocity[1] * dt

        # Keep within boundaries
        new_x = max(self.radius, min(new_x, self.model.width - self.radius))
        new_y = max(self.radius, min(new_y, self.model.height - self.radius))

        # Check for wall collisions
        if self.would_collide_with_wall((new_x, new_y)):
            # Try a reduced movement
            reduced_x = self.position[0] + (new_x - self.position[0]) * 0.1
            reduced_y = self.position[1] + (new_y - self.position[1]) * 0.1

            if not self.would_collide_with_wall((reduced_x, reduced_y)):
                new_x, new_y = reduced_x, reduced_y
            else:
                # Change direction if can't move at all
                self.direction = (self.direction + random.uniform(0.5 * math.pi, 1.5 * math.pi)) % (2 * math.pi)
                self.velocity = (
                    math.cos(self.direction) * self.max_speed * 0.5,
                    math.sin(self.direction) * self.max_speed * 0.5
                )
                return

        # Update position
        old_position = self.position
        self.position = (new_x, new_y)

        # Update spatial grid if position changed
        if old_position != self.position:
            self.model.spatial_grid.update_agent(self)

    def _shoot_at_target(self, target, current_time):
        """Execute shooting logic at a target"""
        # Record the shot
        shot = {
            'start_pos': self.position,
            'end_pos': target.position,
            'start_time': current_time
        }
        self.model.active_shots.append(shot)

        # Play sound if available
        try:
            if hasattr(self.model, 'gunshot_sound') and self.model.gunshot_sound:
                self.model.gunshot_sound.play()
        except Exception as e:
            print(f"Warning: Could not play gunshot sound: {e}")

        # Determine if shot hits
        if random.random() < self.hit_probability:
            print(f"Shooter {self.unique_id} hit agent {target.unique_id}")

            # Play kill sound if available
            try:
                if hasattr(self.model, 'kill_sound') and self.model.kill_sound:
                    self.model.kill_sound.play()
            except Exception as e:
                print(f"Warning: Could not play kill sound: {e}")

            # Remove the target from the model
            self.model.remove_agent(target)
        else:
            print(f"Shooter {self.unique_id} missed")

        # Update last shot time
        self.last_shot_time = current_time

    def search_behavior(self, dt):
        """Behavior for searching for targets when none are visible"""
        # Check if we've been in search mode for too long without finding a target
        search_duration_threshold = 5.0  # seconds

        # Initialize search_start_time if not set
        if not hasattr(self, 'search_start_time'):
            self.search_start_time = self.model.simulation_time
            self.search_direction_change_time = 0

        # Check if time to change direction
        if self.model.simulation_time - self.search_direction_change_time > 2.0:
            # Change direction more often when searching
            self.direction = random.uniform(0, 2 * math.pi)
            self.search_direction_change_time = self.model.simulation_time

        # Set velocity based on direction
        self.velocity = (
            math.cos(self.direction) * self.max_speed * 0.7,  # Move slower while searching
            math.sin(self.direction) * self.max_speed * 0.7
        )

        # Reset search timer if we've been searching too long
        if self.model.simulation_time - self.search_start_time > search_duration_threshold:
            self.search_start_time = self.model.simulation_time
            # More dramatic direction change after long search
            self.direction = random.uniform(0, 2 * math.pi)