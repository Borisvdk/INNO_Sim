import math
import random
import config
import pygame
from agents.schoolagent import SchoolAgent
from a_star import astar
from utilities import has_line_of_sight


class StudentAgent(SchoolAgent):
    """Agent class for students with potential shooter behaviors."""

    def __init__(self, unique_id, model, position, agent_type):
        # Initialize parent class
        super().__init__(unique_id, model, agent_type, position)

        # Student-specific attributes
        self.fear_level = 0.0
        self.grab_weapon_prob = 0.05  # Note: This is defined but not used in step logic
        # self.state = "Normal" # State is implicitly handled by in_emergency now
        self.path = []
        self.in_emergency = False  # This is the primary state indicator
        self.normal_speed = random.uniform(40.0, 60.0)
        self.emergency_speed = random.uniform(60.0, 90.0)

        # Shooter-specific attributes
        self.is_shooter = False
        self.last_shot_time = 0.0
        self.shooting_interval = config.SHOOTING_INTERVAL
        self.shooting_range = config.SHOOTING_RANGE
        self.hit_probability = config.HIT_PROBABILITY
        self.locked_target = None
        self.target_lock_time = 0.0
        self.max_target_lost_time = 2.0
        self.max_target_pursuit_time = 10.0
        self.target_last_seen_time = 0.0
        self.target_lock_distance = 75.0
        self.target_release_distance = 100.0
        self.wall_stuck_time = 0.0
        self.wall_stuck_threshold = 2.0
        self.wall_stuck_position = None
        self.wall_stuck_distance_threshold = 3.0
        self.search_start_time = 0
        self.search_direction_change_time = 0
        self.shooter_start_time = 0.0


    def step_continuous(self, dt):
        """
        Handles student agent behavior: shooter, evacuation (awareness-based), or normal roaming.
        Awareness can be triggered by proximity to a shooter OR a nearby fleeing student (scream).
        """
        if self.is_shooter:
            current_time = self.model.simulation_time

            # Initialize the shooter start time if it's not set yet
            if self.shooter_start_time == 0.0:
                self.shooter_start_time = current_time

        # --- Shooter Behavior ---
        if self.is_shooter:
            # ... (shooter behavior logic remains the same) ...
            current_time = self.model.simulation_time
            target_is_valid = self._validate_locked_target(current_time)
            if not target_is_valid:
                self._find_new_target(current_time)

            if self.locked_target is None:
                self.search_behavior(dt)
            else:
                self._pursue_target(dt, current_time)

            super().move_continuous(dt)  # Use the base class movement logic

        # --- Non-Shooter Behavior ---
        else:
            triggered_emergency_this_step = False  # Flag to calculate path only once

            # --- 1. Awareness Check (Only if not already fleeing) ---
            if not self.in_emergency:
                # --- 1a. Check for nearby SHOOTERS ---
                if self.model.has_active_shooter:
                    for shooter in self.model.active_shooters:
                        # Ensure shooter is still valid
                        if shooter in self.model.schedule:
                            # Calculate squared distance for efficiency
                            dx = shooter.position[0] - self.position[0]
                            dy = shooter.position[1] - self.position[1]
                            dist_squared = dx * dx + dy * dy

                            # Check if within awareness range
                            if dist_squared < config.AWARENESS_RANGE ** 2:
                                print(
                                    f"Student {self.unique_id} detected shooter {shooter.unique_id} nearby! Entering emergency.")
                                self.in_emergency = True
                                triggered_emergency_this_step = True
                                break  # Stop checking other shooters once one is detected

                # --- 1b. Check for nearby SCREAMING students (if not already triggered by shooter) ---
                if not self.in_emergency:
                    # Use spatial grid to find agents within scream radius + a buffer
                    check_radius = config.SCREAM_RADIUS + self.radius  # Check slightly larger area
                    nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, check_radius)
                    scream_radius_sq = config.SCREAM_RADIUS ** 2

                    for agent in nearby_agents:
                        # Check if it's another student, it's fleeing, and it's not self
                        if agent != self and isinstance(agent, StudentAgent) and agent.in_emergency:
                            # Verify actual distance (squared) is within scream radius
                            dx = agent.position[0] - self.position[0]
                            dy = agent.position[1] - self.position[1]
                            dist_squared = dx * dx + dy * dy

                            if dist_squared < scream_radius_sq:
                                print(
                                    f"Student {self.unique_id} heard scream from student {agent.unique_id}! Entering emergency.")
                                self.in_emergency = True
                                triggered_emergency_this_step = True
                                break  # Stop checking other nearby agents once alerted by a scream

            # --- 1c. Calculate Path (if emergency was triggered this step) ---
            if triggered_emergency_this_step:
                # Define exit target
                exit_x_start = 50 * (config.SIM_WIDTH / 60)
                exit_x_end = 58 * (config.SIM_WIDTH / 60)
                exit_y_start = 0
                exit_y_end = 2 * (config.SIM_HEIGHT / 40) + 10
                exit_center_target = ((exit_x_start + exit_x_end) / 2, exit_y_end / 2)

                try:
                    path = astar((self.position[0], self.position[1]),
                                 exit_center_target,
                                 self.model.wall_rects)  # Use pygame.Rect list
                    if path:
                        self.path = path
                        print(f"Student {self.unique_id} calculated path to exit.")
                    else:
                        print(
                            f"⚠️ No path found for student {self.unique_id} at {self.position} after entering emergency.")
                        # Optional: Fallback if no path found (e.g., move away from avg threat)
                except Exception as e:
                    print(f"Error during A* pathfinding for student {self.unique_id}: {e}")
                    # Handle error gracefully

            # --- 2. Action Based on State ---
            # Define exit rect (needed for collision check)
            exit_x_start = 50 * (config.SIM_WIDTH / 60)
            exit_x_end = 58 * (config.SIM_WIDTH / 60)
            exit_y_start = 0
            exit_y_end = 2 * (config.SIM_HEIGHT / 40) + 10
            school_exit = pygame.Rect(exit_x_start, exit_y_start, exit_x_end - exit_x_start, exit_y_end - exit_y_start)
            exit_center_target = (
            (exit_x_start + exit_x_end) / 2, exit_y_end / 2)  # Recalculate here or pass from above

            # --- Emergency Evacuation State (Fleeing) ---
            if self.in_emergency:
                # --- Fleeing Movement Logic ---
                # 1. Check exit collision
                if school_exit.collidepoint(self.position):
                    self.model.remove_agent(self)
                    return  # Agent removed

                # 2. Follow path if available
                if self.path:
                    target_x, target_y = self.path[0]
                    dx, dy = target_x - self.position[0], target_y - self.position[1]
                    dist = math.hypot(dx, dy)
                    move_speed = self.emergency_speed

                    # If close to the next waypoint, snap to it and remove from path
                    # Adjust tolerance based on speed and dt
                    waypoint_tolerance = move_speed * dt * 1.5
                    if dist < waypoint_tolerance:
                        self.position = (target_x, target_y)
                        self.path.pop(0)
                        self.model.spatial_grid.update_agent(self)
                        # If path is now empty, transition to moving towards exit center
                        if not self.path:
                            print(f"Student {self.unique_id} reached end of path, moving towards exit center.")
                    elif dist > 0:  # Move towards waypoint
                        step_dist = move_speed * dt
                        new_x = self.position[0] + (dx / dist) * step_dist
                        new_y = self.position[1] + (dy / dist) * step_dist
                        # Basic boundary clamping
                        new_x = max(self.radius, min(new_x, self.model.width - self.radius))
                        new_y = max(self.radius, min(new_y, self.model.height - self.radius))

                        # Check for wall collision before moving
                        if not self.would_collide_with_wall((new_x, new_y)):
                            old_pos = self.position
                            self.position = (new_x, new_y)
                            if old_pos != self.position:
                                self.model.spatial_grid.update_agent(self)
                        else:
                            # Simple wall collision response: try stopping path following momentarily
                            print(
                                f"Student {self.unique_id} path blocked by wall near {self.position}, trying exit center.")
                            self.path = []  # Clear path to force move towards exit center

                # 3. Move towards exit center if no path (or path blocked)
                else:
                    target_x, target_y = exit_center_target
                    dx, dy = target_x - self.position[0], target_y - self.position[1]
                    dist = math.hypot(dx, dy)
                    move_speed = self.emergency_speed * 0.75  # Slightly slower direct move

                    if dist > self.radius:  # Only move if not already very close
                        step_dist = min(move_speed * dt, dist)  # Don't overshoot
                        if dist > 0:
                            new_x = self.position[0] + (dx / dist) * step_dist
                            new_y = self.position[1] + (dy / dist) * step_dist
                            new_x = max(self.radius, min(new_x, self.model.width - self.radius))
                            new_y = max(self.radius, min(new_y, self.model.height - self.radius))
                            # Check wall collision before moving
                            if not self.would_collide_with_wall((new_x, new_y)):
                                old_pos = self.position
                                self.position = (new_x, new_y)
                                if old_pos != self.position:
                                    self.model.spatial_grid.update_agent(self)
                            else:
                                # Stuck even when moving towards center - maybe try random small nudge?
                                pass  # Avoid getting stuck in loops

                # 4. Simple collision avoidance specific to fleeing agents (optional enhancement)
                self._avoid_student_collisions()  # Apply nudge if overlapping

            # --- Normal Roaming State ---
            else:  # Not in emergency and not a shooter
                self._check_steal_weapon()
                super().move_continuous(dt)  # Use the base class movement logic

    def _check_steal_weapon(self):
        """Check if the student can steal a weapon from an armed adult."""
        # This check should only happen if the student isn't already a shooter/armed
        if self.has_weapon or self.is_shooter:
            return

        # Find nearby adults within steal range
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, config.STEAL_RANGE)
        for agent in nearby_agents:
            # Ensure agent exists and is an adult with a weapon
            if agent not in self.model.schedule or agent.agent_type != "adult" or not agent.has_weapon:
                continue

            # Check distance and line of sight
            dx = agent.position[0] - self.position[0]
            dy = agent.position[1] - self.position[1]
            distance_sq = dx * dx + dy * dy  # Use squared distance for efficiency
            if distance_sq > config.STEAL_RANGE ** 2:
                continue

            # Check LoS only if close enough
            if not self.has_line_of_sight(agent.position):
                continue

            # Attempt to steal based on probability
            if random.random() < config.STEAL_PROBABILITY:
                agent.has_weapon = False
                # Update adult appearance if needed (e.g., color)
                # agent.color = config.COLORS["RED"] # Assuming RED is unarmed adult

                self.has_weapon = True
                self.is_shooter = True
                # Update student appearance
                # self.color = config.COLORS["GREEN"] # Assuming GREEN is shooter
                self.model.active_shooters.add(self)  # Add to model's set
                print(f"Student {self.unique_id} stole weapon from {agent.unique_id} and became a shooter!")

                # Important: Break after successful steal to avoid multiple steals per step
                break

    def _avoid_student_collisions(self):
        """Helper method to apply a simple nudge to prevent students overlapping."""
        # Consider using agent radius for rect size
        agent_rect_size = self.radius * 2
        student_rect = pygame.Rect(
            self.position[0] - agent_rect_size / 2,
            self.position[1] - agent_rect_size / 2,
            agent_rect_size, agent_rect_size
        )

        nudged = False
        # Check against *other* students only
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position,
                                                                  agent_rect_size)  # Use small check radius
        for other in nearby_agents:
            # Check if other agent exists, is a student, is not self, and is close enough
            if other != self and other in self.model.schedule and isinstance(other, StudentAgent):
                other_rect_size = other.radius * 2
                other_rect = pygame.Rect(
                    other.position[0] - other_rect_size / 2,
                    other.position[1] - other_rect_size / 2,
                    other_rect_size, other_rect_size
                )

                if student_rect.colliderect(other_rect):
                    # Apply a small random nudge away from the other agent
                    dx = self.position[0] - other.position[0]
                    dy = self.position[1] - other.position[1]
                    dist = math.hypot(dx, dy)
                    nudge_strength = 0.8  # Slightly stronger nudge for fleeing

                    if dist > 0.1:  # Avoid division by zero / large forces if perfectly overlapped
                        nudge_x = (dx / dist) * nudge_strength
                        nudge_y = (dy / dist) * nudge_strength
                    else:  # Apply random nudge if perfectly overlapped
                        nudge_x = random.uniform(-nudge_strength, nudge_strength)
                        nudge_y = random.uniform(-nudge_strength, nudge_strength)

                    old_pos = self.position
                    new_x = self.position[0] + nudge_x
                    new_y = self.position[1] + nudge_y

                    # Boundary check after nudge
                    new_x = max(self.radius, min(new_x, self.model.width - self.radius))
                    new_y = max(self.radius, min(new_y, self.model.height - self.radius))

                    # Check wall collision after nudge
                    if not self.would_collide_with_wall((new_x, new_y)):
                        self.position = (new_x, new_y)
                        nudged = True
                        # Update grid ONLY if position changed
                        if old_pos != self.position:
                            self.model.spatial_grid.update_agent(self)
                        # Don't break immediately, might need to nudge away from multiple agents
                        # break # Apply only one nudge per step might be okay too

        # No need to return nudged status unless used elsewhere

    def _validate_locked_target(self, current_time):
        """Validate if the currently locked target is still valid and visible."""
        # Basic existence check
        if self.locked_target is None:
            return False

        # Check if target still exists in simulation
        if self.locked_target not in self.model.schedule:
            # print(f"Shooter {self.unique_id} lost target {self.locked_target.unique_id} (removed)")
            self.locked_target = None
            return False

        # Check distance
        target_x, target_y = self.locked_target.position
        dx = target_x - self.position[0]
        dy = target_y - self.position[1]
        distance_squared = dx * dx + dy * dy
        if distance_squared > self.target_release_distance * self.target_release_distance:
            # print(f"Shooter {self.unique_id} released target {self.locked_target.unique_id} (too far)")
            self.locked_target = None
            return False

        # Check pursuit time
        time_since_locked = current_time - self.target_lock_time
        if time_since_locked > self.max_target_pursuit_time:
            # print(f"Shooter {self.unique_id} switching targets after pursuing {self.locked_target.unique_id} too long")
            self.locked_target = None
            return False

        # Check line of sight
        has_sight = self.has_line_of_sight(self.locked_target.position)
        if has_sight:
            self.target_last_seen_time = current_time
            return True
        else:
            # IMPROVED: Reduce time to lose target when it's behind a wall
            # This makes the shooter more realistic in not "remembering" targets
            # that have gone behind walls for too long
            time_since_last_seen = current_time - self.target_last_seen_time
            max_memory_time = min(1.0, self.max_target_lost_time / 2)  # Reduced from default value

            if time_since_last_seen > max_memory_time:
                # print(f"Shooter {self.unique_id} lost target {self.locked_target.unique_id} (out of sight)")
                self.locked_target = None
                return False
            else:
                # Target temporarily hidden but still being pursued
                return True

    def _find_new_target(self, current_time):
        """Find a new target among nearby agents, checking for line of sight."""
        search_radius = self.target_lock_distance
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, search_radius)
        visible_targets = []

        for agent in nearby_agents:
            # Check agent still exists and is valid target type
            if agent != self and agent in self.model.schedule and agent.agent_type in ["student", "adult"]:
                # CRITICAL: Explicit line of sight check before considering a target
                if self.has_line_of_sight(agent.position):
                    dx = self.position[0] - agent.position[0]
                    dy = self.position[1] - agent.position[1]
                    distance_squared = dx * dx + dy * dy
                    # Ensure distance is within lock distance BEFORE adding
                    if distance_squared <= search_radius * search_radius:
                        visible_targets.append((agent, distance_squared))

        if not visible_targets:
            self.locked_target = None  # Ensure target is cleared if none found
            return

        # Sort by distance squared (faster)
        visible_targets.sort(key=lambda x: x[1])
        nearest_agent = visible_targets[0][0]

        # Lock onto the nearest visible target
        self.locked_target = nearest_agent
        self.target_lock_time = current_time
        self.target_last_seen_time = current_time
        # print(f"Shooter {self.unique_id} locked onto {self.locked_target.unique_id}")

    def _pursue_target(self, dt, current_time):
        """Pursue a locked target, moving toward it and shooting when in range and has line of sight."""
        # Ensure we have a valid target
        if self.locked_target is None or self.locked_target not in self.model.schedule:
            return

        target_x, target_y = self.locked_target.position
        dx = target_x - self.position[0]
        dy = target_y - self.position[1]
        distance = math.sqrt(dx * dx + dy * dy)  # Need actual distance here

        # Calculate target angle REGARDLESS of distance
        # This fixes the UnboundLocalError
        target_angle = math.atan2(dy, dx)

        # Check for line of sight to target
        has_sight = self.has_line_of_sight(self.locked_target.position)

        # Check wall stuck logic
        self._check_wall_stuck(dt)

        if distance > self.shooting_range * 0.9:  # Move if outside 90% of shooting range
            self.direction = target_angle  # Set desired direction
            self.target_speed = self.max_speed  # Set desired speed

            # Improved navigation for obscured targets
            if not has_sight:
                # If stuck against a wall, change direction more drastically
                if self.wall_stuck_time > 0.1:
                    print(f"Shooter {self.unique_id} stuck pursuing, changing direction.")
                    # Try turning away from the wall or target slightly
                    self.direction += random.uniform(-math.pi / 2, math.pi / 2)
                    self.direction %= (2 * math.pi)
                    self.wall_stuck_time = 0  # Reset stuck timer after adjustment
                else:
                    # Try to find a path around the obstacle
                    # This is a simple approximation - could be enhanced with pathfinding
                    self.direction += random.uniform(-math.pi / 4, math.pi / 4)
                    self.direction %= (2 * math.pi)
                    self.target_speed *= 0.8  # Slow down a bit when navigating around obstacles

        else:  # In shooting range
            self.target_speed = 0  # Stop trying to move forward
            self.velocity = (0, 0)  # Explicitly stop velocity (base move might override otherwise)

            # Only shoot if we have line of sight AND enough time has elapsed
            if current_time - self.last_shot_time >= self.shooting_interval:
                # CRITICAL: Explicit line of sight check before shooting
                if has_sight:
                    self._shoot_at_target(self.locked_target, current_time)
                else:
                    # If no line of sight but target is in range, try to reposition
                    # This encourages the shooter to move to get a better angle
                    self.target_speed = self.max_speed * 0.5
                    # Try to move perpendicular to target direction to get around obstacles
                    perp_angle = target_angle + (math.pi / 2)
                    perp_direction = random.choice([perp_angle, perp_angle - math.pi]) % (2 * math.pi)
                    self.direction = perp_direction

    def _check_wall_stuck(self, dt):
        """ Checks if the agent is stuck against a wall while pursuing. """
        stuck_dist_sq = self.wall_stuck_distance_threshold ** 2

        if self.wall_stuck_position is None:
            self.wall_stuck_position = self.position
            self.wall_stuck_time = 0
            return

        # Calculate distance moved since last check
        dx = self.position[0] - self.wall_stuck_position[0]
        dy = self.position[1] - self.wall_stuck_position[1]
        dist_moved_sq = dx * dx + dy * dy

        if dist_moved_sq < stuck_dist_sq:
            self.wall_stuck_time += dt
        else:
            # Moved sufficiently, reset timer and position
            self.wall_stuck_time = 0
            self.wall_stuck_position = self.position

        # Consider stuck if hasn't moved much for a certain time
        # if self.wall_stuck_time > self.wall_stuck_threshold:
        #     # Action to take when stuck (handled in _pursue_target now)
        #     pass

    def _shoot_at_target(self, target, current_time):
        """Shoot at a target, but only if there's a clear line of sight."""
        # Ensure target exists before trying to access position
        if target not in self.model.schedule:
            print(f"Shooter {self.unique_id} tried to shoot removed target {target.unique_id}")
            self.locked_target = None
            return

        # CRITICAL FIX: Double-check line of sight before shooting
        # This ensures we never shoot through walls even if target validation
        # temporarily allows targeting when line of sight is lost
        if not self.has_line_of_sight(target.position):
            # Cannot shoot at target behind a wall
            return

        shot = {'start_pos': self.position, 'end_pos': target.position, 'start_time': current_time}
        self.model.active_shots.append(shot)
        if hasattr(self.model, 'gunshot_sound') and self.model.gunshot_sound:
            self.model.gunshot_sound.play()

        if random.random() < self.hit_probability:
            print(f"Shooter {self.unique_id} hit agent {target.unique_id}")
            if hasattr(self.model, 'kill_sound') and self.model.kill_sound:
                self.model.kill_sound.play()

            # Important: Ensure we remove the *correct* target instance
            target_to_remove = target
            if self.locked_target == target_to_remove:
                self.locked_target = None  # Unlock before removing
            self.model.remove_agent(target_to_remove)  # Critical: Remove target

        else:
            # print(f"Shooter {self.unique_id} missed") # Reduce miss noise
            pass

        self.last_shot_time = current_time

    def search_behavior(self, dt):
        # ... (keep existing code, ensure self.velocity/target_speed is set for base move) ...
        # Set target speed and direction for parent's move_continuous
        current_time = self.model.simulation_time
        if not hasattr(self, 'search_start_time') or self.search_start_time == 0:  # Initialize if needed
            self.search_start_time = current_time
            self.search_direction_change_time = 0
            self.direction = random.uniform(0, 2 * math.pi)  # Initial random direction

        # Change direction periodically
        if current_time - self.search_direction_change_time > 3.0:  # Change every 3 seconds
            self.direction = random.uniform(0, 2 * math.pi)
            self.search_direction_change_time = current_time

        self.target_speed = self.max_speed * 0.6  # Move slower while searching
        # Base class move_continuous will handle actual movement and avoidance
