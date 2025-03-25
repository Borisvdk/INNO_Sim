import math
import random

import pygame
from agents.schoolagent import SchoolAgent
from utilities import has_line_of_sight

WIDTH, HEIGHT = 1200, 800


class StudentAgent(SchoolAgent):
    """Agent class for students with potential shooter behaviors."""

    def __init__(self, unique_id, model, position, agent_type):
        # Initialize parent class
        super().__init__(unique_id, model, agent_type, position)

        # Student-specific attributes
        self.fear_level = 0.0
        self.grab_weapon_prob = 0.05
        self.state = "Normal"

        self.path = []
        self.reached_exit = False
        self.in_emergency = False

        # Shooter-specific attributes
        self.is_shooter = False
        self.last_shot_time = 0.0
        self.shooting_interval = 2.0  # Shoot every 2 seconds
        self.shooting_range = 10.0  # Stop and shoot within 10 units
        self.hit_probability = 0.5  # 50% chance to hit
        self.locked_target = None  # Added target locking attribute
        self.target_lock_time = 0.0  # Time when target was locked
        self.max_target_lost_time = 5.0  # Maximum time to keep pursuing a target after losing sight (seconds)
        self.target_last_seen_time = 0.0  # Time when target was last seen
        self.target_lock_distance = 150.0  # Maximum distance to initially lock a target (units)
        self.target_release_distance = 200.0  # Distance at which to release a locked target (units)

        # Search behavior tracking
        self.search_start_time = 0
        self.search_direction_change_time = 0

    def at_exit(self):
        return self.position[0] <= 0 or self.position[0] >= WIDTH or self.position[1] <= 0 or self.position[1] >= HEIGHT

    def step_continuous(self, dt):
        """Moves students at normal speed toward the exit and removes them if they reach it."""

        # Define the exit area
        school_exit = pygame.Rect(500, 18, 80, 6)  # Slightly larger for better detection

        # Ensure students use their normal speed
        normal_speed = getattr(self, 'normal_speed', 1.0)  # Use default speed if not set

        if not self.is_shooter:
            if self.path:
                target_x, target_y = self.path[0]
                dx, dy = target_x - self.position[0], target_y - self.position[1]
                dist = math.hypot(dx, dy)

                if dist < normal_speed:  # Move at normal speed
                    self.position = (target_x, target_y)
                    self.path.pop(0)
                else:
                    self.position = (
                        self.position[0] + (dx / dist) * normal_speed,
                        self.position[1] + (dy / dist) * normal_speed
                    )

            # Check if student is inside the exit area
            student_rect = pygame.Rect(self.position[0] - 5, self.position[1] - 5, 10, 10)
            if student_rect.colliderect(school_exit):
                print(f"✅ Student at {self.position} exited safely!")
                self.model.remove_agent(self)
                return

            # Prevent students from getting stuck by nudging them apart slightly
            for other in self.model.schedule:
                if other != self and other.agent_type == "student":
                    other_rect = pygame.Rect(other.position[0] - 5, other.position[1] - 5, 10, 10)
                    if student_rect.colliderect(other_rect):
                        self.position = (
                            self.position[0] + random.uniform(-0.25, 0.25),
                            self.position[1] + random.uniform(-0.25, 0.25)
                        )


            # If the agent is a shooter, follow the shooter logic
            super().step_continuous(dt)

            return  # Prevent shooter logic from running

        # Shooter-specific behavior with line of sight
        current_time = self.model.simulation_time

        # Validate current locked target (if exists)
        target_is_valid = self._validate_locked_target(current_time)

        # If no valid target, find a new one
        if not target_is_valid:
            self._find_new_target(current_time)

        # Handle shooter movement and shooting based on target status
        if self.locked_target is None:
            # No target - search behavior
            self.search_behavior(dt)
        else:
            # We have a target - pursue and attempt to shoot
            self._pursue_target(dt, current_time)

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

    def _validate_locked_target(self, current_time):
        """Validate if current locked target is still valid."""
        if self.locked_target is None:
            return False

        # Check if locked target still exists in model
        if self.locked_target not in self.model.schedule:
            print(f"Shooter {self.unique_id} lost target {self.locked_target.unique_id} (removed from simulation)")
            self.locked_target = None
            return False

        # Calculate distance to locked target
        target_x, target_y = self.locked_target.position
        dx = target_x - self.position[0]
        dy = target_y - self.position[1]
        distance_squared = dx * dx + dy * dy

        # Release target if too far away
        if distance_squared > self.target_release_distance * self.target_release_distance:
            print(f"Shooter {self.unique_id} released target {self.locked_target.unique_id} (too far away)")
            self.locked_target = None
            return False

        # Check if target is visible
        has_sight = self.has_line_of_sight(self.locked_target.position)

        if has_sight:
            # Update last seen time if visible
            self.target_last_seen_time = current_time
            return True
        else:
            # Check if we've lost sight for too long
            time_since_last_seen = current_time - self.target_last_seen_time
            if time_since_last_seen > self.max_target_lost_time:
                print(f"Shooter {self.unique_id} lost target {self.locked_target.unique_id} (out of sight too long)")
                self.locked_target = None
                return False
            else:
                # Still pursuing despite temporary loss of sight
                return True

    def _find_new_target(self, current_time):
        """Find and lock onto a new target."""
        # Search for potential targets
        search_radius = self.target_lock_distance
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, search_radius)

        # Filter for valid targets (visible and not self)
        visible_targets = []
        for agent in nearby_agents:
            if agent != self and agent.agent_type in ["student", "adult"]:
                if self.has_line_of_sight(agent.position):
                    # Calculate distance for sorting
                    dx = self.position[0] - agent.position[0]
                    dy = self.position[1] - agent.position[1]
                    distance_squared = dx * dx + dy * dy
                    visible_targets.append((agent, distance_squared))

        # If no visible targets, return
        if not visible_targets:
            return

        # Sort by distance and select closest
        visible_targets.sort(key=lambda x: x[1])
        nearest_agent = visible_targets[0][0]

        # Lock onto this target
        self.locked_target = nearest_agent
        self.target_lock_time = current_time
        self.target_last_seen_time = current_time
        print(f"Shooter {self.unique_id} locked onto new target {self.locked_target.unique_id}")

    def _pursue_target(self, dt, current_time):
        """Pursue locked target and attempt to shoot when in range."""
        target_x, target_y = self.locked_target.position
        dx = target_x - self.position[0]
        dy = target_y - self.position[1]
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > self.shooting_range:
            # Move toward locked target
            # Normalize direction
            inv_dist = 1.0 / distance
            direction_x = dx * inv_dist
            direction_y = dy * inv_dist

            # Set velocity directly
            self.velocity = (direction_x * self.max_speed, direction_y * self.max_speed)
        else:
            # Within shooting range - stop and attempt to shoot
            self.velocity = (0, 0)

            # Try to shoot if enough time has passed and we have line of sight
            if current_time - self.last_shot_time >= self.shooting_interval:
                has_sight = self.has_line_of_sight(self.locked_target.position)
                if has_sight:
                    self._shoot_at_target(self.locked_target, current_time)

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

            # Clear locked target if this was it
            if self.locked_target == target:
                self.locked_target = None

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