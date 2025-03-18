from agents.schoolagent import SchoolAgent

import math
import random


class StudentAgent(SchoolAgent):
    def __init__(self, unique_id, model, position, agent_type, agents):
        super().__init__(unique_id, model, position, agent_type, agents)
        # Student-specific attributes are initialized in the parent class

    def step_continuous(self, dt):
        """Optimized version of step_continuous with shooter behavior integrated"""
        if not self.is_shooter:
            # Use standard movement for non-shooters
            super().step_continuous(dt)
            return

        # Shooter-specific behavior
        current_time = self.model.simulation_time

        # Find target agents in a single pass
        search_radius = max(self.shooting_range * 1.5, 50.0)  # Slightly larger than shooting range
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, search_radius)
        valid_targets = [agent for agent in nearby_agents
                         if agent != self and agent.agent_type in ["student", "adult"]]

        if not valid_targets:
            # No targets? Apply slight random movement
            self.direction += random.uniform(-0.2, 0.2)
            target_vx = self.max_speed * 0.5 * math.cos(self.direction)
            target_vy = self.max_speed * 0.5 * math.sin(self.direction)
            self.velocity = (target_vx, target_vy)
        else:
            # Find nearest target in one pass
            nearest_agent = None
            min_distance_squared = float('inf')

            for agent in valid_targets:
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

                # Set velocity directly - shooters don't need complex movement
                self.velocity = (direction_x * self.max_speed, direction_y * self.max_speed)
            else:
                # Within shooting range - stop and attempt to shoot
                self.velocity = (0, 0)

                # Try to shoot if enough time has passed
                if current_time - self.last_shot_time >= self.shooting_interval:
                    self._shoot_at_target(nearest_agent, current_time)

        # Update position with both boundary and wall checks
        new_x = self.position[0] + self.velocity[0] * dt
        new_y = self.position[1] + self.velocity[1] * dt

        # Keep the shooter within boundaries
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
                self.direction = (self.direction + math.pi) % (2 * math.pi)
                self.velocity = (-self.velocity[0] * 0.5, -self.velocity[1] * 0.5)
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