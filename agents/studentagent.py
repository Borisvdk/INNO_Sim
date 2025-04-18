import math
import random
import pygame
import config
from agents.schoolagent import SchoolAgent
from a_star import astar
from utilities import distance_squared


class StudentAgent(SchoolAgent):
    """Agent class for students with evacuation and potential shooter behaviors."""

    def __init__(self, unique_id, model, position, agent_type):
        """
        Initialize a StudentAgent.

        Args:
            unique_id: A unique identifier for the agent.
            model: The model instance the agent belongs to.
            position: The initial (x, y) position of the agent.
            agent_type: The type of agent (should be "student").
        """
        super().__init__(unique_id, model, agent_type, position)

        self.in_emergency = False
        self.normal_speed = random.uniform(40.0, 60.0)
        self.emergency_speed = random.uniform(config.STUDENT_MAX_SPEED * 0.8, config.STUDENT_MAX_SPEED * 1.1)
        self.path = []
        self.target_exit_rect = None
        self.target_exit_center = None

        self.is_shooter = False
        self.last_shot_time = 0.0
        self.shooting_interval = config.SHOOTING_INTERVAL
        self.shooting_range = config.SHOOTING_RANGE
        self.hit_probability = config.HIT_PROBABILITY

        self.locked_target = None
        self.target_lock_time = 0.0
        self.target_last_seen_time = 0.0
        self.target_lock_distance = config.SHOOTING_RANGE
        self.target_release_distance = config.SHOOTING_RANGE * 1.2
        self.max_target_lost_time = 2.0
        self.max_target_pursuit_time = 10.0

        self.wall_stuck_time = 0.0
        self.wall_stuck_position = None
        self.wall_stuck_threshold = 1.0
        self.wall_stuck_distance_threshold = self.radius * 0.5

        self.search_start_time = 0
        self.search_direction_change_time = 0
        self.shooter_start_time = 0.0

    def step_continuous(self, dt):
        """
        Perform one time step, delegating to shooter or standard student behavior.

        Args:
            dt: The time step duration.
        """
        if self.is_shooter:
            self._handle_shooter_behavior(dt)
        else:
            self._handle_student_behavior(dt)

    def _handle_shooter_behavior(self, dt):
        """
        Handle behavior logic when the student is an active shooter.

        Args:
            dt: The time step duration.
        """
        current_time = self.model.simulation_time

        if self.shooter_start_time == 0.0:
            self.shooter_start_time = current_time

        if not self._validate_locked_target(current_time):
            self._find_new_target(current_time)

        if self.locked_target is None:
            self._search_behavior(dt, current_time)
        else:
            self._pursue_target(dt, current_time)

        super().move_continuous(dt)

    def _handle_student_behavior(self, dt):
        """
        Handle behavior logic for a non-shooter student (normal or emergency).

        Args:
            dt: The time step duration.
        """
        if not self.in_emergency:
            self._check_shooter_awareness()
            if not self.in_emergency and config.ENABLE_STUDENT_SCREAMING:
                # Check if this student hears another student screaming (Doing by Talking / Talking by Doing).
                self._check_for_screams()

            if self.in_emergency:
                self._calculate_evacuation_path()

        if self.in_emergency:
            if self._check_exit_reached():
                return

            self._follow_evacuation_path(dt)

            self.target_speed = self.emergency_speed
            super().move_continuous(dt)
        else:
            self._check_steal_weapon()
            super().move_continuous(dt)


    def _check_shooter_awareness(self):
        """
        Check if the student becomes aware of a shooter by sight or hearing gunshots.

        Returns:
            bool: True if awareness was triggered, False otherwise.
        """
        if not self.model.has_active_shooter:
            return False

        awareness_range_sq = config.AWARENESS_RANGE ** 2

        for shooter in self.model.active_shooters:
            if shooter not in self.model.schedule: continue

            dist_squared = distance_squared(self.position, shooter.position)
            if dist_squared < awareness_range_sq:
                 if self.has_line_of_sight(shooter.position):
                    self.in_emergency = True
                    print(f"Student {self.unique_id} spotted shooter {shooter.unique_id}! Entering emergency.")
                    return True

        recent_shot_time_limit = 2.0
        gunshot_awareness_range_sq = (config.AWARENESS_RANGE * 1.5) ** 2

        for shot in self.model.active_shots:
             if self.model.simulation_time - shot['start_time'] < recent_shot_time_limit:
                 dist_sq = distance_squared(self.position, shot['start_pos'])
                 if dist_sq < gunshot_awareness_range_sq:
                     self.in_emergency = True
                     print(f"Student {self.unique_id} heard recent gunshot! Entering emergency.")
                     return True

        return False

    def _check_for_screams(self):
        """
        Check if this student hears screams from nearby students already in emergency.
        This implements awareness spreading via screams ("Doing by Talking" or "Talking by Doing").
        The 'doing' (fleeing state of another student) implies 'talking' (a scream),
        which causes this student to 'do' (enter emergency state).

        Returns:
            bool: True if awareness was triggered by hearing a scream, False otherwise.
        """
        scream_radius_sq = config.SCREAM_RADIUS ** 2
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, config.SCREAM_RADIUS)

        for agent in nearby_agents:
            if (agent != self and
                    agent in self.model.schedule and
                    isinstance(agent, StudentAgent) and
                    getattr(agent, 'in_emergency', False)):

                dist_squared = distance_squared(self.position, agent.position)
                if dist_squared < scream_radius_sq:
                    if self.has_line_of_sight(agent.position):
                        # Hearing scream (implied talking) causes Doing (entering emergency).
                        self.in_emergency = True
                        print(f"Student {self.unique_id} heard scream from student {agent.unique_id}! Entering emergency.")
                        return True

        return False

    def _calculate_evacuation_path(self):
        """
        Find the nearest exit and calculate an A* path towards it, avoiding walls.
        """
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

            try:
                path = astar(
                    self.position,
                    self.target_exit_center,
                    self.model.wall_rects
                )

                if path:
                    if not path or distance_squared(path[-1], self.target_exit_center) > 1:
                        path.append(self.target_exit_center)
                    self.path = path
                    print(f"Student {self.unique_id} calculated path to exit at {self.target_exit_center}.")
                else:
                    print(f"⚠️ No A* path found for student {self.unique_id} to {self.target_exit_center}. Will move directly.")
                    self.path = [self.target_exit_center]
            except Exception as e:
                print(f"Error during pathfinding for student {self.unique_id} to {self.target_exit_center}: {e}")
                self.path = [self.target_exit_center]
        else:
             print(f"⚠️ Student {self.unique_id}: Could not find any exits.")
             self.path = []


    def _check_exit_reached(self):
        """
        Check if the student has reached the vicinity of any exit zone.

        Returns:
            bool: True if an exit was reached (and agent removed), False otherwise.
        """
        agent_rect = pygame.Rect(
            self.position[0] - self.radius,
            self.position[1] - self.radius,
            self.radius * 2,
            self.radius * 2
        )

        inflation_amount = self.radius * 2

        if self.target_exit_rect:
            inflated_target_exit = self.target_exit_rect.inflate(inflation_amount, inflation_amount)
            if agent_rect.colliderect(inflated_target_exit):
                print(f"Student {self.unique_id} reached vicinity of targeted exit {self.target_exit_rect.center}!")
                self.model.remove_agent(self, reason="escaped")
                return True

        for exit_rect in self.model.exits:
             if self.target_exit_rect and exit_rect == self.target_exit_rect:
                  continue

             inflated_exit = exit_rect.inflate(inflation_amount, inflation_amount)
             if agent_rect.colliderect(inflated_exit):
                 print(f"Student {self.unique_id} reached vicinity of alternative exit {exit_rect.center}!")
                 self.model.remove_agent(self, reason="escaped")
                 return True

        return False


    def _follow_evacuation_path(self, dt):
        """
        Move the student along the pre-calculated A* path or directly towards the target exit.

        Args:
            dt: The time step duration.
        """
        if not self.path and self.target_exit_center:
            self.path = [self.target_exit_center]
        elif not self.path and not self.target_exit_center:
             self.target_speed = 0
             self.velocity = (0,0)
             return

        target_waypoint = self.path[0]
        target_x, target_y = target_waypoint

        dx = target_x - self.position[0]
        dy = target_y - self.position[1]
        dist_to_waypoint = math.hypot(dx, dy)

        waypoint_reach_tolerance = self.emergency_speed * dt * 1.5

        if dist_to_waypoint < waypoint_reach_tolerance:
            self.position = target_waypoint
            self.path.pop(0)

            if not self.path:
                print(f"Student {self.unique_id} reached end of calculated path near exit.")
                if self.target_exit_center:
                     dx_final = self.target_exit_center[0] - self.position[0]
                     dy_final = self.target_exit_center[1] - self.position[1]
                     if dx_final != 0 or dy_final != 0:
                           self.direction = math.atan2(dy_final, dx_final)
                self.target_speed = self.emergency_speed
            else:
                 next_target_x, next_target_y = self.path[0]
                 dx_next = next_target_x - self.position[0]
                 dy_next = next_target_y - self.position[1]
                 if dx_next != 0 or dy_next != 0:
                      self.direction = math.atan2(dy_next, dx_next)
                 self.target_speed = self.emergency_speed

        elif dist_to_waypoint > 0:
            self.direction = math.atan2(dy, dx)
            self.target_speed = self.emergency_speed


    def _check_steal_weapon(self):
        """
        Attempt to steal a weapon from a nearby armed adult, potentially becoming a shooter.
        """
        if self.has_weapon or self.is_shooter or self.in_emergency:
            return

        steal_range_sq = config.STEAL_RANGE ** 2
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, config.STEAL_RANGE)

        for agent in nearby_agents:
            if (agent in self.model.schedule and
                    agent.agent_type == "adult" and
                    getattr(agent, 'has_weapon', False)):

                dist_squared = distance_squared(self.position, agent.position)
                if dist_squared < steal_range_sq:
                    if self.has_line_of_sight(agent.position):
                        if random.random() < config.STEAL_PROBABILITY:
                            agent.has_weapon = False
                            self.has_weapon = True
                            self.is_shooter = True
                            self.model.active_shooters.add(self)
                            print(f"!!! Student {self.unique_id} stole weapon from Adult {agent.unique_id} and became a shooter!")
                            self.path = []
                            self.in_emergency = False
                            self.shooter_start_time = self.model.simulation_time
                            self._find_new_target(self.model.simulation_time)
                            break

    def _validate_locked_target(self, current_time):
        """
        Check if the current shooter target is still valid (exists, within range, visible, etc.).

        Args:
            current_time: The current simulation time.

        Returns:
            bool: True if the target is still valid, False otherwise.
        """
        if self.locked_target is None:
            return False

        if self.locked_target not in self.model.schedule:
            self.locked_target = None
            return False

        dist_squared = distance_squared(self.position, self.locked_target.position)
        if dist_squared > self.target_release_distance ** 2:
            self.locked_target = None
            return False

        if current_time - self.target_lock_time > self.max_target_pursuit_time:
            print(f"Shooter {self.unique_id} giving up on target {self.locked_target.unique_id} due to pursuit time.")
            self.locked_target = None
            return False

        has_sight = self.has_line_of_sight(self.locked_target.position)
        if has_sight:
            self.target_last_seen_time = current_time
            return True
        else:
            time_since_seen = current_time - self.target_last_seen_time
            if time_since_seen > self.max_target_lost_time:
                 print(f"Shooter {self.unique_id} lost sight of target {self.locked_target.unique_id} for too long.")
                 self.locked_target = None
                 return False
            return True

    def _find_new_target(self, current_time):
        """
        Find a new target (closest visible student or adult) for the shooter.

        Args:
            current_time: The current simulation time.
        """
        search_radius = self.target_lock_distance
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, search_radius)
        visible_targets = []

        for agent in nearby_agents:
            if (agent != self and
                    agent in self.model.schedule and
                    agent.agent_type in ["student", "adult"] and
                    not getattr(agent, 'is_shooter', False)):

                if self.has_line_of_sight(agent.position):
                    dist_squared = distance_squared(self.position, agent.position)
                    if dist_squared <= self.target_lock_distance ** 2:
                        visible_targets.append((agent, dist_squared))

        if not visible_targets:
            self.locked_target = None
            return

        visible_targets.sort(key=lambda x: x[1])
        self.locked_target = visible_targets[0][0]
        self.target_lock_time = current_time
        self.target_last_seen_time = current_time
        print(f"Shooter {self.unique_id} locked target: {self.locked_target.unique_id} ({self.locked_target.agent_type})")

    def _pursue_target(self, dt, current_time):
        """
        Handle shooter's movement and engagement logic when pursuing a locked target.

        Args:
            dt: The time step duration.
            current_time: The current simulation time.
        """
        if self.locked_target is None or self.locked_target not in self.model.schedule:
            self.locked_target = None
            return

        target_pos = self.locked_target.position
        dx = target_pos[0] - self.position[0]
        dy = target_pos[1] - self.position[1]
        distance_sq = dx * dx + dy * dy
        distance = math.sqrt(distance_sq)

        if distance > 1e-6:
            target_angle = math.atan2(dy, dx)
            self.direction = target_angle

        has_sight = self.has_line_of_sight(target_pos)

        effective_shooting_range = self.shooting_range * 0.95

        if distance > effective_shooting_range:
            self.target_speed = self.max_speed

            if not has_sight:
                 self.direction += random.uniform(-math.pi / 6, math.pi / 6)
                 self.target_speed *= 0.8

        else:
            if has_sight:
                self.target_speed = 0
                self.velocity = (0, 0)

                if current_time - self.last_shot_time >= self.shooting_interval:
                    self._shoot_at_target(self.locked_target, current_time)
            else:
                self.target_speed = self.max_speed * 0.4
                perp_angle_offset = random.choice([-math.pi / 2, math.pi / 2])
                self.direction = (target_angle + perp_angle_offset) % (2 * math.pi)

    def _shoot_at_target(self, target, current_time):
        """
        Perform the action of shooting at the specified target.

        Args:
            target: The agent being targeted.
            current_time: The current simulation time.
        """
        if target not in self.model.schedule:
            self.locked_target = None
            return

        if not self.has_line_of_sight(target.position):
            return

        shot_data = {
            'start_pos': self.position,
            'end_pos': target.position,
            'start_time': current_time
        }
        self.model.active_shots.append(shot_data)

        if hasattr(self.model, 'gunshot_sound') and self.model.gunshot_sound:
            self.model.gunshot_sound.play()

        if random.random() < self.hit_probability:
            print(f"HIT: Shooter {self.unique_id} hit target {target.unique_id} ({target.agent_type})")

            if hasattr(self.model, 'kill_sound') and self.model.kill_sound:
                self.model.kill_sound.play()

            if self.locked_target == target:
                self.locked_target = None
            self.model.remove_agent(target, reason="died")
        else:
            pass

        self.last_shot_time = current_time


    def _search_behavior(self, dt, current_time):
        """
        Define the shooter's movement behavior when no target is locked (wandering/searching).

        Args:
            dt: The time step duration.
            current_time: The current simulation time.
        """
        self._check_wall_stuck(dt)

        if self.search_start_time == 0:
            self.search_start_time = current_time
            self.search_direction_change_time = current_time
            self.direction = random.uniform(0, 2 * math.pi)

        change_interval = config.SHOOTER_SEARCH_DURATION
        if (current_time - self.search_direction_change_time > change_interval
            or self.wall_stuck_time > self.wall_stuck_threshold):

            self.direction = random.uniform(0, 2 * math.pi)
            self.search_direction_change_time = current_time
            if self.wall_stuck_time > self.wall_stuck_threshold:
                 self.wall_stuck_time = 0
                 self.wall_stuck_position = self.position

        self.target_speed = self.max_speed * 0.6


    def _check_wall_stuck(self, dt):
         """
         Monitor if the agent has been stuck in approximately the same location for too long.

         Args:
             dt: The time step duration.
         """
         if self.wall_stuck_position is None:
              self.wall_stuck_position = self.position
              self.wall_stuck_time = 0
              return

         dist_sq_moved = distance_squared(self.position, self.wall_stuck_position)

         if dist_sq_moved < self.wall_stuck_distance_threshold ** 2:
              self.wall_stuck_time += dt
         else:
              self.wall_stuck_time = 0
              self.wall_stuck_position = self.position