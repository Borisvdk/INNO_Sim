import math
import random
import config
import pygame
from agents.schoolagent import SchoolAgent
from a_star import astar
from utilities import has_line_of_sight, distance_squared


class StudentAgent(SchoolAgent):
    """Agent class for students with evacuation and potential shooter behaviors."""

    def __init__(self, unique_id, model, position, agent_type):
        # Initialize parent class
        super().__init__(unique_id, model, agent_type, position)

        # Student state
        self.in_emergency = False
        self.normal_speed = random.uniform(40.0, 60.0)
        self.emergency_speed = random.uniform(60.0, 90.0)
        self.path = []
        self.target_exit_rect = None
        self.target_exit_center = None

        # Shooter attributes
        self.is_shooter = False
        self.last_shot_time = 0.0
        self.shooting_interval = config.SHOOTING_INTERVAL
        self.shooting_range = config.SHOOTING_RANGE
        self.hit_probability = config.HIT_PROBABILITY

        # Target tracking
        self.locked_target = None
        self.target_lock_time = 0.0
        self.target_last_seen_time = 0.0
        self.target_lock_distance = 75.0
        self.target_release_distance = 100.0
        self.max_target_lost_time = 2.0
        self.max_target_pursuit_time = 10.0

        # Wall avoidance
        self.wall_stuck_time = 0.0
        self.wall_stuck_position = None
        self.wall_stuck_threshold = 2.0
        self.wall_stuck_distance_threshold = 3.0

        # Search behavior
        self.search_start_time = 0
        self.search_direction_change_time = 0
        self.shooter_start_time = 0.0

    def step_continuous(self, dt):
        """Main step function that delegates to appropriate behavior handler."""
        if self.is_shooter:
            self._handle_shooter_behavior(dt)
        else:
            self._handle_student_behavior(dt)

    def _handle_shooter_behavior(self, dt):
        """Handle behavior when student is a shooter."""
        current_time = self.model.simulation_time

        # Initialize start time if first time
        if self.shooter_start_time == 0.0:
            self.shooter_start_time = current_time

        # Target acquisition
        if not self._validate_locked_target(current_time):
            self._find_new_target(current_time)

        # Act based on target state
        if self.locked_target is None:
            self._search_behavior(dt)
        else:
            self._pursue_target(dt, current_time)

        # Base movement handles actual position update
        super().move_continuous(dt)

    def _handle_student_behavior(self, dt):
        """Handle non-shooter student behavior."""
        # Check for emergency triggers if not already fleeing
        if not self.in_emergency:
            # Check for shooter awareness
            self._check_shooter_awareness()

            # Check for other students' screams
            if not self.in_emergency and config.ENABLE_STUDENT_SCREAMING:
                self._check_for_screams()

            # Calculate evacuation path if emergency was just triggered
            if self.in_emergency:
                self._calculate_evacuation_path()

        # Handle evacuation movement if in emergency
        if self.in_emergency:
            # Check if reached an exit
            if self._check_exit_reached():
                return  # Student escaped, was removed from simulation

            # Follow evacuation path
            self._follow_evacuation_path(dt)

            # Avoid collisions with other students
            self._avoid_student_collisions()
        else:
            # Normal behavior
            self._check_steal_weapon()
            super().move_continuous(dt)

    def _check_shooter_awareness(self):
        """Check if student becomes aware of a nearby shooter."""
        if not self.model.has_active_shooter:
            return False

        awareness_range_sq = config.AWARENESS_RANGE ** 2

        for shooter in self.model.active_shooters:
            if shooter not in self.model.schedule:
                continue

            dist_squared = distance_squared(self.position, shooter.position)
            if dist_squared < awareness_range_sq:
                self.in_emergency = True
                print(f"Student {self.unique_id} detected shooter {shooter.unique_id}! Entering emergency.")
                return True

        return False

    def _check_for_screams(self):
        """Check if student hears screams from nearby students in emergency."""
        scream_radius_sq = config.SCREAM_RADIUS ** 2
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, config.SCREAM_RADIUS)

        for agent in nearby_agents:
            if (agent != self and
                    agent in self.model.schedule and
                    isinstance(agent, StudentAgent) and
                    agent.in_emergency):

                dist_squared = distance_squared(self.position, agent.position)
                if dist_squared < scream_radius_sq:
                    self.in_emergency = True
                    print(f"Student {self.unique_id} heard scream from student {agent.unique_id}! Entering emergency.")
                    return True

        return False

    def _calculate_evacuation_path(self):
        """Find nearest exit and calculate path to it."""
        # Find closest exit
        closest_exit_rect = None
        min_dist_sq = float('inf')

        if not self.model.exits:
            print(f"⚠️ Student {self.unique_id}: No exits defined! Cannot calculate path.")
            self.target_exit_center = None
            self.target_exit_rect = None
            self.path = []
            return

        for exit_rect in self.model.exits:
            dist_sq = distance_squared(self.position, exit_rect.center)
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_exit_rect = exit_rect

        if closest_exit_rect:
            self.target_exit_rect = closest_exit_rect
            self.target_exit_center = closest_exit_rect.center

            # Calculate A* path
            try:
                path = astar(
                    self.position,
                    self.target_exit_center,
                    self.model.wall_rects
                )

                if path:
                    self.path = path
                    print(f"Student {self.unique_id} found path to exit at {self.target_exit_center}.")
                else:
                    print(f"⚠️ No path found for student {self.unique_id}. Moving directly.")
                    self.path = []
            except Exception as e:
                print(f"Error during pathfinding for student {self.unique_id}: {e}")
                self.path = []

    def _check_exit_reached(self):
        """Check if student has reached an exit."""
        agent_rect = pygame.Rect(
            self.position[0] - self.radius,
            self.position[1] - self.radius,
            self.radius * 2,
            self.radius * 2
        )

        for exit_rect in self.model.exits:
            if exit_rect.colliderect(agent_rect):
                print(f"Student {self.unique_id} reached exit!")
                self.model.remove_agent(self, reason="escaped")
                return True

        return False

    def _follow_evacuation_path(self, dt):
        """Move along evacuation path or directly to exit."""
        # Follow path if available
        if self.path:
            target_x, target_y = self.path[0]
            dx, dy = target_x - self.position[0], target_y - self.position[1]
            dist = math.hypot(dx, dy)
            move_speed = self.emergency_speed
            waypoint_tolerance = move_speed * dt * 1.5

            if dist < waypoint_tolerance:
                # Reached waypoint, move to next
                self.position = (target_x, target_y)
                self.path.pop(0)
                self.model.spatial_grid.update_agent(self)

                if not self.path:
                    print(f"Student {self.unique_id} reached end of path.")
            elif dist > 0:
                # Move toward waypoint
                step_dist = move_speed * dt
                new_x = self.position[0] + (dx / dist) * step_dist
                new_y = self.position[1] + (dy / dist) * step_dist
                new_x = max(self.radius, min(new_x, self.model.width - self.radius))
                new_y = max(self.radius, min(new_y, self.model.height - self.radius))

                if not self.would_collide_with_wall((new_x, new_y)):
                    old_pos = self.position
                    self.position = (new_x, new_y)
                    if old_pos != self.position:
                        self.model.spatial_grid.update_agent(self)
                else:
                    # Path blocked by wall, clear path to try direct movement
                    self.path = []

        # Direct movement to exit if no path or path emptied
        elif self.target_exit_center:
            target_x, target_y = self.target_exit_center
            dx, dy = target_x - self.position[0], target_y - self.position[1]
            dist = math.hypot(dx, dy)

            if dist > self.radius:
                # Move toward exit
                move_speed = self.emergency_speed * 0.75
                step_dist = min(move_speed * dt, dist)

                if dist > 0:
                    new_x = self.position[0] + (dx / dist) * step_dist
                    new_y = self.position[1] + (dy / dist) * step_dist
                    new_x = max(self.radius, min(new_x, self.model.width - self.radius))
                    new_y = max(self.radius, min(new_y, self.model.height - self.radius))

                    if not self.would_collide_with_wall((new_x, new_y)):
                        old_pos = self.position
                        self.position = (new_x, new_y)
                        if old_pos != self.position:
                            self.model.spatial_grid.update_agent(self)

    def _avoid_student_collisions(self):
        """Apply simple collision avoidance with other students."""
        agent_size = self.radius * 2
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, agent_size)

        for other in nearby_agents:
            if other == self or other not in self.model.schedule or not isinstance(other, StudentAgent):
                continue

            # Calculate collision bounds
            self_rect = pygame.Rect(
                self.position[0] - self.radius,
                self.position[1] - self.radius,
                self.radius * 2,
                self.radius * 2
            )

            other_rect = pygame.Rect(
                other.position[0] - other.radius,
                other.position[1] - other.radius,
                other.radius * 2,
                other.radius * 2
            )

            if self_rect.colliderect(other_rect):
                # Apply nudge away from other student
                dx = self.position[0] - other.position[0]
                dy = self.position[1] - other.position[1]
                dist = math.hypot(dx, dy)
                nudge_strength = 0.8

                if dist > 0.1:
                    nudge_x = (dx / dist) * nudge_strength
                    nudge_y = (dy / dist) * nudge_strength
                else:
                    # Random direction if perfectly overlapped
                    nudge_x = random.uniform(-nudge_strength, nudge_strength)
                    nudge_y = random.uniform(-nudge_strength, nudge_strength)

                # Apply nudge with boundary and wall checks
                new_x = self.position[0] + nudge_x
                new_y = self.position[1] + nudge_y
                new_x = max(self.radius, min(new_x, self.model.width - self.radius))
                new_y = max(self.radius, min(new_y, self.model.height - self.radius))

                if not self.would_collide_with_wall((new_x, new_y)):
                    old_pos = self.position
                    self.position = (new_x, new_y)
                    if old_pos != self.position:
                        self.model.spatial_grid.update_agent(self)

    def _check_steal_weapon(self):
        """Attempt to steal weapon from armed adult."""
        if self.has_weapon or self.is_shooter:
            return

        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, config.STEAL_RANGE)

        for agent in nearby_agents:
            if (agent not in self.model.schedule or
                    agent.agent_type != "adult" or
                    not agent.has_weapon):
                continue

            # Check distance and line of sight
            dist_squared = distance_squared(self.position, agent.position)
            if dist_squared > config.STEAL_RANGE ** 2:
                continue

            if not self.has_line_of_sight(agent.position):
                continue

            # Attempt steal based on probability
            if random.random() < config.STEAL_PROBABILITY:
                agent.has_weapon = False
                self.has_weapon = True
                self.is_shooter = True
                self.model.active_shooters.add(self)
                print(f"Student {self.unique_id} stole weapon from {agent.unique_id} and became a shooter!")
                break

    def _validate_locked_target(self, current_time):
        """Check if current target is still valid."""
        if self.locked_target is None:
            return False

        # Check if target still exists
        if self.locked_target not in self.model.schedule:
            self.locked_target = None
            return False

        # Check distance
        dist_squared = distance_squared(self.position, self.locked_target.position)
        if dist_squared > self.target_release_distance ** 2:
            self.locked_target = None
            return False

        # Check pursuit time
        if current_time - self.target_lock_time > self.max_target_pursuit_time:
            self.locked_target = None
            return False

        # Check line of sight
        has_sight = self.has_line_of_sight(self.locked_target.position)
        if has_sight:
            self.target_last_seen_time = current_time
            return True
        else:
            # Lose target if out of sight too long
            time_since_seen = current_time - self.target_last_seen_time
            max_memory_time = min(1.0, self.max_target_lost_time / 2)

            if time_since_seen > max_memory_time:
                self.locked_target = None
                return False
            return True  # Still tracking but temporarily lost sight

    def _find_new_target(self, current_time):
        """Find new target from visible nearby agents."""
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, self.target_lock_distance)
        visible_targets = []

        for agent in nearby_agents:
            if (agent == self or
                    agent not in self.model.schedule or
                    agent.agent_type not in ["student", "adult"]):
                continue

            if self.has_line_of_sight(agent.position):
                dist_squared = distance_squared(self.position, agent.position)
                if dist_squared <= self.target_lock_distance ** 2:
                    visible_targets.append((agent, dist_squared))

        if not visible_targets:
            return

        # Target closest visible agent
        visible_targets.sort(key=lambda x: x[1])
        self.locked_target = visible_targets[0][0]
        self.target_lock_time = current_time
        self.target_last_seen_time = current_time

    def _pursue_target(self, dt, current_time):
        """Pursue and engage locked target."""
        if self.locked_target is None or self.locked_target not in self.model.schedule:
            return

        # Calculate distance and direction to target
        target_pos = self.locked_target.position
        dx = target_pos[0] - self.position[0]
        dy = target_pos[1] - self.position[1]
        distance = math.sqrt(dx * dx + dy * dy)
        target_angle = math.atan2(dy, dx)

        # Check line of sight and wall stuck status
        has_sight = self.has_line_of_sight(target_pos)
        self._check_wall_stuck(dt)

        if distance > self.shooting_range * 0.9:
            # Move toward target
            self.direction = target_angle
            self.target_speed = self.max_speed

            # Handle obstacles
            if not has_sight and self.wall_stuck_time > 0.1:
                # Change direction if stuck
                self.direction += random.uniform(-math.pi / 2, math.pi / 2)
                self.direction %= (2 * math.pi)
                self.wall_stuck_time = 0
            elif not has_sight:
                # Try to navigate around obstacle
                self.direction += random.uniform(-math.pi / 4, math.pi / 4)
                self.direction %= (2 * math.pi)
                self.target_speed *= 0.8
        else:
            # In shooting range - stop and shoot if possible
            self.target_speed = 0
            self.velocity = (0, 0)

            if has_sight and current_time - self.last_shot_time >= self.shooting_interval:
                self._shoot_at_target(self.locked_target, current_time)
            elif not has_sight:
                # Try to reposition for line of sight
                self.target_speed = self.max_speed * 0.5
                perp_angle = target_angle + (math.pi / 2)
                self.direction = random.choice([perp_angle, perp_angle - math.pi]) % (2 * math.pi)

    def _check_wall_stuck(self, dt):
        """Track if agent is stuck against a wall."""
        if self.wall_stuck_position is None:
            self.wall_stuck_position = self.position
            self.wall_stuck_time = 0
            return

        # Check if moved since last position
        dist_squared = distance_squared(self.position, self.wall_stuck_position)

        if dist_squared < self.wall_stuck_distance_threshold ** 2:
            self.wall_stuck_time += dt
        else:
            self.wall_stuck_time = 0
            self.wall_stuck_position = self.position

    def _shoot_at_target(self, target, current_time):
        """Attempt to shoot target."""
        # Verify target is valid
        if target not in self.model.schedule:
            self.locked_target = None
            return

        # Double-check line of sight
        if not self.has_line_of_sight(target.position):
            return

        # Create shot visualization and play sound
        shot = {'start_pos': self.position, 'end_pos': target.position, 'start_time': current_time}
        self.model.active_shots.append(shot)

        if hasattr(self.model, 'gunshot_sound') and self.model.gunshot_sound:
            self.model.gunshot_sound.play()

        # Determine if hit
        if random.random() < self.hit_probability:
            print(f"Shooter {self.unique_id} hit agent {target.unique_id}")

            if hasattr(self.model, 'kill_sound') and self.model.kill_sound:
                self.model.kill_sound.play()

            # Clear target reference before removal
            if self.locked_target == target:
                self.locked_target = None

            self.model.remove_agent(target, reason="died")

        self.last_shot_time = current_time

    def _search_behavior(self, dt):
        """Random search when no target locked."""
        current_time = self.model.simulation_time

        # Initialize if first time
        if self.search_start_time == 0:
            self.search_start_time = current_time
            self.search_direction_change_time = 0
            self.direction = random.uniform(0, 2 * math.pi)

        # Change direction periodically
        if current_time - self.search_direction_change_time > 3.0:
            self.direction = random.uniform(0, 2 * math.pi)
            self.search_direction_change_time = current_time

        self.target_speed = self.max_speed * 0.6
