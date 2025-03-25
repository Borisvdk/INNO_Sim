import math
import random
import config
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
        self.normal_speed = random.uniform(40.0, 60.0)  # Speed for normal movement

        # Shooter-specific attributes
        self.is_shooter = False
        self.last_shot_time = 0.0
        self.shooting_interval = 2.0  # Shoot every 2 seconds
        self.shooting_range = 10.0  # Stop and shoot within 10 units
        self.hit_probability = 0.5  # 50% chance to hit
        self.locked_target = None  # Added target locking attribute
        self.target_lock_time = 0.0  # Time when target was locked
        self.max_target_lost_time = 2.0  # Maximum time to keep pursuing a target after losing sight (seconds)
        self.max_target_pursuit_time = 10.0  # Maximum time to pursue any single target before switching
        self.target_last_seen_time = 0.0  # Time when target was last seen
        self.target_lock_distance = 75.0  # Maximum distance to initially lock a target (units)
        self.target_release_distance = 100.0  # Distance at which to release a locked target (units)

        # Wall avoidance parameters
        self.wall_stuck_time = 0.0  # Time when agent started being stuck at a wall
        self.wall_stuck_threshold = 2.0  # Time threshold to consider being "stuck" (seconds)
        self.wall_stuck_position = None  # Position where the agent got stuck
        self.wall_stuck_distance_threshold = 3.0  # Distance to consider the agent still stuck

        # Search behavior tracking
        self.search_start_time = 0
        self.search_direction_change_time = 0

        # Shooter timeout tracking
        self.shooter_start_time = 0.0  # To track when the shooter becomes active

    def at_exit(self):
        return self.position[0] <= 0 or self.position[0] >= WIDTH or self.position[1] <= 0 or self.position[1] >= HEIGHT

    def step_continuous(self, dt):
        """
        Handles student agent movement. Students will:
        1. Follow evacuation path during emergencies
        2. Roam around randomly during normal operation
        3. Execute shooter behavior if they are a shooter
        """
        # Define the exit area
        school_exit = pygame.Rect(500, 18, 80, 6)  # Slightly larger for better detection

        # Ensure students use their normal speed
        normal_speed = getattr(self, 'normal_speed', 1.0)  # Use default speed if not set

        # If the agent is a shooter, track the time they have been active
        if self.is_shooter:
            current_time = self.model.simulation_time

            # Initialize the shooter start time if it's not set yet
            if self.shooter_start_time == 0.0:
                self.shooter_start_time = current_time

            # If 10 seconds have passed since the shooter became active, remove the shooter
            if current_time - self.shooter_start_time >= 60.0:
                print(f"Shooter {self.unique_id} removed from simulation after 10 seconds.")
                self.model.remove_agent(self)
                return  # End the step to remove the shooter immediately

        if not self.is_shooter and not self.has_weapon:
            # Attempt to steal a weapon from nearby adults
            nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, config.STEAL_RANGE)
            for agent in nearby_agents:
                if agent.agent_type == "adult" and agent.has_weapon:
                    if random.random() < config.STEAL_PROBABILITY:
                        # Stealing successful
                        agent.has_weapon = False
                        self.has_weapon = True
                        self.is_shooter = True
                        self.model.active_shooters.add(self)
                        self.color = config.COLORS["GREEN"]
                        print(f"Student {self.unique_id} stole a weapon from adult {agent.unique_id} "
                              f"and became a shooter!")
                        break  # Only steal from one adult per step

        if not self.is_shooter:
            # Normal student behavior
            if self.path:
                target_x, target_y = self.path[0]
                dx, dy = target_x - self.position[0], target_y - self.position[1]
                dist = math.hypot(dx, dy)

                # Use normal_speed for movement
                if dist < self.normal_speed * dt:  # If close enough to reach in this step
                    self.position = (target_x, target_y)
                    self.path.pop(0)
                else:
                    # Move toward next waypoint
                    self.position = (
                        self.position[0] + (dx / dist) * self.normal_speed * dt,
                        self.position[1] + (dy / dist) * self.normal_speed * dt
                    )

                # Check if student reached exit
                student_rect = pygame.Rect(self.position[0] - 5, self.position[1] - 5, 10, 10)
                if student_rect.colliderect(school_exit):
                    print(f"✅ Student at {self.position} exited safely!")
                    self.model.remove_agent(self)
                    return

                # Avoid collisions with other students
                self._avoid_student_collisions()

                self._check_steal_weapon()
            else:
                # NORMAL MODE - roam around when no emergency path is set
                # Use the parent class's continuous movement logic
                super().move_continuous(dt)

                # Additional collision avoidance with other students
                self._avoid_student_collisions()

            return  # Prevent shooter logic from running if not a shooter

        # SHOOTER LOGIC (unchanged from your improved version)
        # If the agent is a shooter, follow the shooter logic
        super().step_continuous(dt)

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

        # Update position with improved wall collision handling
        new_x = self.position[0] + self.velocity[0] * dt
        new_y = self.position[1] + self.velocity[1] * dt

        # Keep within boundaries
        new_x = max(self.radius, min(new_x, self.model.width - self.radius))
        new_y = max(self.radius, min(new_y, self.model.height - self.radius))

        # Check for wall collisions with more intelligent handling
        if self.would_collide_with_wall((new_x, new_y)):
            wall_collision = True

            # First, try to move in just X direction
            x_only_pos = (new_x, self.position[1])
            if not self.would_collide_with_wall(x_only_pos):
                new_y = self.position[1]
                wall_collision = False

            # Then try to move in just Y direction
            y_only_pos = (self.position[0], new_y)
            if not self.would_collide_with_wall(y_only_pos):
                new_x = self.position[0]
                wall_collision = False

            # If both individual axis movements fail, try sliding along the wall
            if wall_collision:
                # Try 8 different angles to find a way around the wall
                for angle_offset in [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75]:
                    # Try angles in both directions
                    for direction_mult in [1, -1]:
                        slide_angle = (self.direction + direction_mult * angle_offset * math.pi) % (2 * math.pi)
                        slide_dist = self.max_speed * dt * 0.5  # Move at half speed when navigating around walls

                        slide_x = self.position[0] + math.cos(slide_angle) * slide_dist
                        slide_y = self.position[1] + math.sin(slide_angle) * slide_dist

                        if not self.would_collide_with_wall((slide_x, slide_y)):
                            new_x, new_y = slide_x, slide_y
                            wall_collision = False
                            # Slightly update direction to better navigate around the wall
                            if self.locked_target:
                                # Gradually turn back toward target
                                target_x, target_y = self.locked_target.position
                                target_angle = math.atan2(target_y - slide_y, target_x - slide_x)
                                self.direction = (0.8 * slide_angle + 0.2 * target_angle) % (2 * math.pi)
                            else:
                                self.direction = slide_angle
                            break

                # If all else fails, move away from the wall
                if wall_collision:
                    # Try a reduced movement as a last resort
                    reduced_x = self.position[0] + (new_x - self.position[0]) * 0.1
                    reduced_y = self.position[1] + (new_y - self.position[1]) * 0.1

                    if not self.would_collide_with_wall((reduced_x, reduced_y)):
                        new_x, new_y = reduced_x, reduced_y
                    else:
                        # Change direction more drastically if we're truly stuck
                        old_direction = self.direction
                        self.direction = (self.direction + math.pi + random.uniform(-0.5, 0.5)) % (2 * math.pi)
                        print(
                            f"Shooter {self.unique_id} is stuck at wall, reversing direction from {old_direction:.2f} to {self.direction:.2f}")

                        # Reduce velocity to prevent bouncing behavior
                        self.velocity = (
                            math.cos(self.direction) * self.max_speed * 0.3,
                            math.sin(self.direction) * self.max_speed * 0.3
                        )

                        # If we have a target and have been stuck for a while, try to find a new path
                        if self.locked_target and random.random() < 0.2:  # 20% chance to try new approach
                            print(
                                f"Shooter {self.unique_id} trying new approach to target {self.locked_target.unique_id}")

                        return

        # Update position
        old_position = self.position
        self.position = (new_x, new_y)

        # Update spatial grid if position changed
        if old_position != self.position:
            self.model.spatial_grid.update_agent(self)

    def _check_steal_weapon(self):
        """Check if the student can steal a weapon from an armed adult."""
        if self.has_weapon or self.is_shooter:
            return

        # Find nearby adults within steal range
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, config.STEAL_RANGE)
        for agent in nearby_agents:
            if agent.agent_type == "adult" and agent.has_weapon:
                # Check distance and line of sight
                dx = agent.position[0] - self.position[0]
                dy = agent.position[1] - self.position[1]
                distance_sq = dx ** 2 + dy ** 2
                if distance_sq > config.STEAL_RANGE ** 2:
                    continue
                if not self.has_line_of_sight(agent.position):
                    continue

                # Attempt to steal
                if random.random() < config.STEAL_PROBABILITY:
                    agent.has_weapon = False
                    self.has_weapon = True
                    self.is_shooter = True
                    print(f"Student {self.unique_id} stole a weapon from adult {agent.unique_id} and became a shooter!")
                    break

    def _avoid_student_collisions(self):
        """Helper method to prevent students from overlapping."""
        student_rect = pygame.Rect(self.position[0] - 5, self.position[1] - 5, 10, 10)

        for other in self.model.schedule:
            if other != self and other.agent_type == "student":
                other_rect = pygame.Rect(other.position[0] - 5, other.position[1] - 5, 10, 10)
                if student_rect.colliderect(other_rect):
                    # Apply a stronger nudge to separate overlapping students
                    self.position = (
                        self.position[0] + random.uniform(-1.0, 1.0),
                        self.position[1] + random.uniform(-1.0, 1.0)
                    )
                    break  # Only apply one nudge per update to avoid jitter

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
            print(
                f"Shooter {self.unique_id} released target {self.locked_target.unique_id} (too far away: {math.sqrt(distance_squared):.1f} units)")
            self.locked_target = None
            return False

        # IMPROVED: Check if we've been pursuing this target for too long overall
        time_since_locked = current_time - self.target_lock_time
        if time_since_locked > self.max_target_pursuit_time:
            print(
                f"Shooter {self.unique_id} switching targets after pursuing {self.locked_target.unique_id} for {time_since_locked:.1f}s")
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
                print(
                    f"Shooter {self.unique_id} lost target {self.locked_target.unique_id} (out of sight for {time_since_last_seen:.1f}s)")
                self.locked_target = None
                return False
            else:
                # IMPROVED: More detailed logging for debugging sight issues
                if random.random() < 0.05:  # Only print occasionally to avoid spam
                    print(
                        f"Shooter {self.unique_id} can't see target {self.locked_target.unique_id}, but still pursuing (time since last seen: {time_since_last_seen:.1f}s)")
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
                # Check if we have line of sight to this agent
                has_sight = self.has_line_of_sight(agent.position)

                # Debug output to check line of sight
                if not has_sight and random.random() < 0.01:  # Only print occasionally
                    print(f"Shooter {self.unique_id} cannot see agent {agent.unique_id} - wall blocking sight")

                if has_sight:
                    # Calculate distance for sorting
                    dx = self.position[0] - agent.position[0]
                    dy = self.position[1] - agent.position[1]
                    distance_squared = dx * dx + dy * dy
                    visible_targets.append((agent, distance_squared))

                    # Optional debug output
                    if random.random() < 0.05:  # Only print occasionally
                        print(
                            f"Shooter {self.unique_id} can see agent {agent.unique_id} at distance {math.sqrt(distance_squared):.1f}")

        # If no visible targets, return
        if not visible_targets:
            if random.random() < 0.1:  # Only print occasionally
                print(f"Shooter {self.unique_id} found no visible targets within range")
            return

        # Sort by distance and select closest
        visible_targets.sort(key=lambda x: x[1])
        nearest_agent = visible_targets[0][0]
        nearest_distance = math.sqrt(visible_targets[0][1])

        # Double-check line of sight before locking
        if not self.has_line_of_sight(nearest_agent.position):
            print(f"ERROR: Line of sight check failed on target acquisition for agent {nearest_agent.unique_id}")
            return

        # Lock onto this target
        self.locked_target = nearest_agent
        self.target_lock_time = current_time
        self.target_last_seen_time = current_time
        print(
            f"Shooter {self.unique_id} locked onto new target {self.locked_target.unique_id} at distance {nearest_distance:.1f} with confirmed line of sight")

    def _pursue_target(self, dt, current_time):
        """Pursue locked target and attempt to shoot when in range."""
        target_x, target_y = self.locked_target.position
        dx = target_x - self.position[0]
        dy = target_y - self.position[1]
        distance = math.sqrt(dx * dx + dy * dy)

        # Check if we have line of sight to target
        has_sight = self.has_line_of_sight(self.locked_target.position)

        if distance > self.shooting_range:
            # Calculate direction to target
            target_angle = math.atan2(dy, dx)

            # If we can see the target, move directly toward it
            if has_sight:
                # Reset wall stuck tracking when we have a clear path
                self.wall_stuck_time = 0.0
                self.wall_stuck_position = None

                # Normalize direction
                inv_dist = 1.0 / distance
                direction_x = dx * inv_dist
                direction_y = dy * inv_dist

                # Set velocity directly
                self.velocity = (direction_x * self.max_speed, direction_y * self.max_speed)
                self.direction = target_angle
            else:
                # Can't see target - use pathfinding-like approach
                # First check if we're stuck near a wall
                current_pos = self.position

                # Initialize wall stuck tracking if needed
                if self.wall_stuck_position is None:
                    self.wall_stuck_position = current_pos
                    self.wall_stuck_time = current_time

                # Calculate how long and how far we've been near this spot
                time_stuck = current_time - self.wall_stuck_time
                dist_moved = math.sqrt((current_pos[0] - self.wall_stuck_position[0]) ** 2 +
                                       (current_pos[1] - self.wall_stuck_position[1]) ** 2)

                # If we've moved far enough, we're not stuck anymore
                if dist_moved > self.wall_stuck_distance_threshold:
                    self.wall_stuck_position = current_pos
                    self.wall_stuck_time = current_time
                    time_stuck = 0

                # If we've been stuck for too long, use more aggressive wall avoidance
                if time_stuck > self.wall_stuck_threshold:
                    # Try to find a way around by choosing a different direction
                    # This creates a random exploration pattern when stuck
                    wall_avoidance_force_x, wall_avoidance_force_y = self.calculate_wall_avoidance()

                    # If there's a significant avoidance force, use it for guidance
                    if abs(wall_avoidance_force_x) > 0.1 or abs(wall_avoidance_force_y) > 0.1:
                        # Normalize avoidance force
                        force_mag = math.sqrt(wall_avoidance_force_x ** 2 + wall_avoidance_force_y ** 2)
                        norm_force_x = wall_avoidance_force_x / force_mag
                        norm_force_y = wall_avoidance_force_y / force_mag

                        # Combine with a bit of randomness to avoid loops
                        random_angle = random.uniform(0, 2 * math.pi)
                        random_factor = 0.3  # How much randomness to inject

                        # Final direction combines wall avoidance with some randomness
                        direction_x = norm_force_x * (1 - random_factor) + math.cos(random_angle) * random_factor
                        direction_y = norm_force_y * (1 - random_factor) + math.sin(random_angle) * random_factor

                        # Update velocity and direction
                        self.direction = math.atan2(direction_y, direction_x)
                        self.velocity = (direction_x * self.max_speed * 0.7,
                                         direction_y * self.max_speed * 0.7)

                        # Print debug info
                        if random.random() < 0.05:  # Only print occasionally to avoid spam
                            print(f"Shooter {self.unique_id} is taking evasive action to navigate around obstacles")
                    else:
                        # If no clear wall avoidance direction, just pick a random new direction
                        new_direction = (target_angle + random.uniform(-math.pi / 2, math.pi / 2)) % (2 * math.pi)
                        self.direction = new_direction
                        self.velocity = (math.cos(new_direction) * self.max_speed * 0.7,
                                         math.sin(new_direction) * self.max_speed * 0.7)
                else:
                    # Not stuck (yet) - continue toward target with small random variations
                    # to help find a path around obstacles
                    direction_variation = random.uniform(-0.3, 0.3)  # Small variation in radians
                    move_direction = target_angle + direction_variation

                    # Set velocity with the varied direction
                    self.direction = move_direction
                    self.velocity = (math.cos(move_direction) * self.max_speed * 0.8,
                                     math.sin(move_direction) * self.max_speed * 0.8)
        else:
            # Within shooting range - stop and attempt to shoot
            self.velocity = (0, 0)

            # Reset wall stuck tracking when in shooting range
            self.wall_stuck_time = 0.0
            self.wall_stuck_position = None

            # Try to shoot if enough time has passed and we have line of sight
            if current_time - self.last_shot_time >= self.shooting_interval:
                if has_sight:
                    self._shoot_at_target(self.locked_target, current_time)
                else:
                    # IMPROVED: Log when shooter can't shoot due to loss of sight
                    if random.random() < 0.1:  # Only print occasionally
                        print(
                            f"Shooter {self.unique_id} is in range but can't shoot target {self.locked_target.unique_id} - no line of sight")

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
