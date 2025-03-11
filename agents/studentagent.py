from agents.schoolagent import SchoolAgent

import math
import random


class StudentAgent(SchoolAgent):
    def __init__(self, unique_id, model, position, agent_type, agents):
        super().__init__(unique_id, model, agent_type, position, agents)
        self.fear_level = 0.0
        self.grab_weapon_prob = 0.05
        self.state = "Normal"

        # Shooter-specific attributes
        self.is_shooter = False
        self.last_shot_time = 0.0
        self.shooting_interval = 2.0  # Shoot every 2 seconds
        self.shooting_range = 10.0  # Stop and shoot within 10 units
        self.hit_probability = 0.5  # 50% chance to hit

    def step_continuous(self, dt):
        """Perform actions for a continuous time step."""
        super().step_continuous(dt)  # Handle basic movement
        if self.is_shooter:
            self.shoot_if_possible()

    def shoot_if_possible(self):
        """Attempt to shoot a nearby agent if the shooting interval has passed."""
        current_time = self.model.simulation_time
        if current_time - self.last_shot_time >= self.shooting_interval:
            # Find agents within shooting range
            nearby_agents = self.get_nearby_agents(self.shooting_range)
            if nearby_agents:
                # Select a random target
                target = random.choice(nearby_agents)

                # Play gunshot sound (shot is fired)
                self.model.gunshot_sound.play()

                # Attempt to hit the target
                if random.random() < self.hit_probability:
                    # Play kill sound (shot hits and kills)
                    self.model.kill_sound.play()
                    print(f"Shooter {self.unique_id} hit agent {target.unique_id}")
                    self.model.remove_agent(target)
                else:
                    print(f"Shooter {self.unique_id} missed")

                # Update the last shot time
                self.last_shot_time = current_time

    def get_nearby_agents(self, radius):
        """Get all agents within a given radius, excluding self."""
        nearby = self.model.spatial_grid.get_nearby_agents(self.position, radius)
        return [agent for agent in nearby if agent != self]

    def move_continuous(self, dt):
        """Handle movement; shooters seek targets, others move normally."""
        if self.is_shooter:
            self.seek_nearest_agent(dt)
        else:
            super().move_continuous(dt)

    def seek_nearest_agent(self, dt):
        """Move toward the nearest agent, stopping within shooting range."""
        nearest_agent = self.find_nearest_agent()
        if nearest_agent:
            # Calculate distance to the target
            dx = nearest_agent.position[0] - self.position[0]
            dy = nearest_agent.position[1] - self.position[1]
            distance = math.sqrt(dx * dx + dy * dy)

            if distance > self.shooting_range:
                # Move toward the target if outside shooting range
                direction_x = dx / distance
                direction_y = dy / distance
                self.velocity = (direction_x * self.max_speed, direction_y * self.max_speed)
            else:
                # Stop moving if within shooting range
                self.velocity = (0, 0)
        else:
            # No target? Stop moving
            self.velocity = (0, 0)

        # Update position based on velocity
        new_x = self.position[0] + self.velocity[0] * dt
        new_y = self.position[1] + self.velocity[1] * dt

        # Keep the shooter within boundaries
        new_x = max(self.radius, min(new_x, self.model.width - self.radius))
        new_y = max(self.radius, min(new_y, self.model.height - self.radius))
        self.position = (new_x, new_y)

    def find_nearest_agent(self):
        """Find the closest agent to the shooter."""
        search_radius = 50.0  # Adjust as needed
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, search_radius)

        min_distance_squared = float('inf')
        nearest_agent = None

        for agent in nearby_agents:
            if agent != self and agent.agent_type in ["student", "adult"]:
                dx = self.position[0] - agent.position[0]
                dy = self.position[1] - agent.position[1]
                distance_squared = dx * dx + dy * dy
                if distance_squared < min_distance_squared:
                    min_distance_squared = distance_squared
                    nearest_agent = agent

        return nearest_agent