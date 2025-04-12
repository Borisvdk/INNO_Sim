import math
import random
import pygame # Import pygame for Rect operations
import config
from agents.schoolagent import SchoolAgent
from a_star import astar
from utilities import distance_squared


class StudentAgent(SchoolAgent):
    """Agent class for students with evacuation and potential shooter behaviors."""

    def __init__(self, unique_id, model, position, agent_type):
        # Initialize parent class
        super().__init__(unique_id, model, agent_type, position)

        # Student state
        self.in_emergency = False
        self.normal_speed = random.uniform(40.0, 60.0) # Consider linking to config if needed
        self.emergency_speed = random.uniform(config.STUDENT_MAX_SPEED * 0.8, config.STUDENT_MAX_SPEED * 1.1) # Use max speed from config
        self.path = []
        self.target_exit_rect = None
        self.target_exit_center = None
        # self.escape_distance_threshold = self.radius * 1.5 # Removed - logic simplified

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
        self.target_lock_distance = config.SHOOTING_RANGE # Lock targets within shooting range initially
        self.target_release_distance = config.SHOOTING_RANGE * 1.2 # Release slightly further away
        self.max_target_lost_time = 2.0
        self.max_target_pursuit_time = 10.0

        # Wall avoidance / Stuck detection
        self.wall_stuck_time = 0.0
        self.wall_stuck_position = None
        self.wall_stuck_threshold = 1.0 # Time threshold to be considered stuck
        self.wall_stuck_distance_threshold = self.radius * 0.5 # Distance threshold for movement

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

        if self.shooter_start_time == 0.0:
            self.shooter_start_time = current_time

        if not self._validate_locked_target(current_time):
            self._find_new_target(current_time)

        if self.locked_target is None:
            self._search_behavior(dt, current_time)
        else:
            self._pursue_target(dt, current_time)

        # Base movement handles actual position update based on set velocity/direction
        super().move_continuous(dt)

    def _handle_student_behavior(self, dt):
        """Handle non-shooter student behavior."""
        # Check for emergency triggers if not already fleeing
        if not self.in_emergency:
            self._check_shooter_awareness()
            if not self.in_emergency and config.ENABLE_STUDENT_SCREAMING:
                self._check_for_screams()

            # Calculate evacuation path ONLY if emergency was just triggered
            if self.in_emergency:
                self._calculate_evacuation_path()

        # Handle evacuation movement if in emergency
        if self.in_emergency:
            # Check if reached an exit (or is near one)
            if self._check_exit_reached(): # This now uses the modified logic
                return  # Student escaped, was removed from simulation

            # Follow evacuation path or move towards exit
            self._follow_evacuation_path(dt)

            # Normal movement handles agent/wall avoidance
            self.target_speed = self.emergency_speed # Ensure moving at emergency speed
            super().move_continuous(dt) # Let base class handle physics/collisions
        else:
            # Normal non-emergency behavior
            self._check_steal_weapon()
            # Let base class handle normal wandering/idle behavior
            super().move_continuous(dt)


    def _check_shooter_awareness(self):
        """Check if student becomes aware of a nearby shooter."""
        if not self.model.has_active_shooter:
            return False

        awareness_range_sq = config.AWARENESS_RANGE ** 2

        for shooter in self.model.active_shooters:
            if shooter not in self.model.schedule: continue # Skip removed shooters

            dist_squared = distance_squared(self.position, shooter.position)
            if dist_squared < awareness_range_sq:
                 # Check line of sight for direct awareness
                 if self.has_line_of_sight(shooter.position):
                    self.in_emergency = True
                    print(f"Student {self.unique_id} spotted shooter {shooter.unique_id}! Entering emergency.")
                    return True

        # Check for nearby gunshots (indirect awareness)
        recent_shot_time_limit = 2.0 # Seconds
        gunshot_awareness_range_sq = (config.AWARENESS_RANGE * 1.5) ** 2 # Hear shots further away

        for shot in self.model.active_shots:
             # Check if shot is recent enough
             if self.model.simulation_time - shot['start_time'] < recent_shot_time_limit:
                 dist_sq = distance_squared(self.position, shot['start_pos'])
                 if dist_sq < gunshot_awareness_range_sq:
                     self.in_emergency = True
                     print(f"Student {self.unique_id} heard recent gunshot! Entering emergency.")
                     return True # Become aware from hearing shot

        return False

    def _check_for_screams(self):
        """Check if student hears screams from nearby students in emergency."""
        scream_radius_sq = config.SCREAM_RADIUS ** 2
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, config.SCREAM_RADIUS)

        for agent in nearby_agents:
            # Check if agent is a student, still active, and in emergency
            if (agent != self and
                    agent in self.model.schedule and
                    isinstance(agent, StudentAgent) and # Ensure it's a StudentAgent instance
                    getattr(agent, 'in_emergency', False)): # Safely check in_emergency

                dist_squared = distance_squared(self.position, agent.position)
                if dist_squared < scream_radius_sq:
                    # Check line of sight for scream audibility (optional realism)
                    if self.has_line_of_sight(agent.position):
                        self.in_emergency = True
                        print(f"Student {self.unique_id} heard scream from student {agent.unique_id}! Entering emergency.")
                        return True # Become aware from hearing scream

        return False

    def _calculate_evacuation_path(self):
        """Find nearest available exit and calculate path to it using A*."""
        closest_exit_rect = None
        min_dist_sq = float('inf')

        if not self.model.exits:
            print(f"⚠️ Student {self.unique_id}: No exits defined! Cannot calculate path.")
            self.target_exit_center = None
            self.target_exit_rect = None
            self.path = []
            return

        # Find the closest exit center point
        for exit_rect in self.model.exits:
            dist_sq = distance_squared(self.position, exit_rect.center)
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_exit_rect = exit_rect

        if closest_exit_rect:
            self.target_exit_rect = closest_exit_rect
            self.target_exit_center = closest_exit_rect.center # Target the center of the exit rect

            # Calculate A* path using the model's wall_rects
            try:
                # Pathfind towards the center of the exit rectangle
                path = astar(
                    self.position,
                    self.target_exit_center,
                    self.model.wall_rects # Use wall rects from model
                )

                if path:
                    # Add the final target center to the path if A* doesn't quite reach it
                    if not path or distance_squared(path[-1], self.target_exit_center) > 1:
                        path.append(self.target_exit_center)
                    self.path = path
                    print(f"Student {self.unique_id} calculated path to exit at {self.target_exit_center}.")
                else:
                    print(f"⚠️ No A* path found for student {self.unique_id} to {self.target_exit_center}. Will move directly.")
                    self.path = [self.target_exit_center] # Set path to just the target point
            except Exception as e:
                print(f"Error during pathfinding for student {self.unique_id} to {self.target_exit_center}: {e}")
                self.path = [self.target_exit_center] # Fallback to direct movement
        else:
             print(f"⚠️ Student {self.unique_id}: Could not find any exits.")
             self.path = []


    def _check_exit_reached(self):
        """Check if the student's bounding box collides with an *inflated* exit rectangle."""

        # Create a rectangle representing the agent's physical space
        agent_rect = pygame.Rect(
            self.position[0] - self.radius, # Left edge
            self.position[1] - self.radius, # Top edge
            self.radius * 2,                # Width
            self.radius * 2                 # Height
        )

        # Define how much to inflate the exit rect (e.g., by the agent's radius)
        # This means the agent is considered 'at the exit' when it's within one radius distance
        # Adjust this value if needed
        inflation_amount = self.radius * 2 # Inflate by agent diameter for wider reach

        # Check the targeted exit first if available
        if self.target_exit_rect:
            # Create an inflated version of the target exit rect
            inflated_target_exit = self.target_exit_rect.inflate(inflation_amount, inflation_amount)
            if agent_rect.colliderect(inflated_target_exit):
                print(f"Student {self.unique_id} reached vicinity of targeted exit {self.target_exit_rect.center}!")
                self.model.remove_agent(self, reason="escaped")
                return True

        # Fallback: Check all exits if no target exit assigned or not inside the target one yet
        # This helps if the agent gets pushed into a different exit
        for exit_rect in self.model.exits:
             # Avoid double-checking the target exit if it exists
             if self.target_exit_rect and exit_rect == self.target_exit_rect:
                  continue

             # Create an inflated version of this exit rect
             inflated_exit = exit_rect.inflate(inflation_amount, inflation_amount)
             # Check if the agent's rectangle collides with this inflated exit
             if agent_rect.colliderect(inflated_exit):
                 print(f"Student {self.unique_id} reached vicinity of alternative exit {exit_rect.center}!")
                 self.model.remove_agent(self, reason="escaped")
                 return True

        return False # Did not collide with any inflated exit zone


    def _follow_evacuation_path(self, dt):
        """Move along the calculated A* path or directly towards the exit center."""
        if not self.path and self.target_exit_center:
            # If no path (e.g., A* failed), set path to just the target
            self.path = [self.target_exit_center]
        elif not self.path and not self.target_exit_center:
            # No path and no target, cannot move for evacuation
             self.target_speed = 0
             self.velocity = (0,0)
             return

        target_waypoint = self.path[0]
        target_x, target_y = target_waypoint

        dx = target_x - self.position[0]
        dy = target_y - self.position[1]
        dist_to_waypoint = math.hypot(dx, dy)

        # Define tolerance for reaching a waypoint based on speed and dt
        # Waypoint is considered reached if the agent can pass it in the next step
        waypoint_reach_tolerance = self.emergency_speed * dt * 1.5

        if dist_to_waypoint < waypoint_reach_tolerance:
            # Reached or very close to the current waypoint
            self.position = target_waypoint # Snap to waypoint
            self.path.pop(0) # Move to the next waypoint

            # If that was the last waypoint, stop trying to follow path
            if not self.path:
                print(f"Student {self.unique_id} reached end of calculated path near exit.")
                # Agent will now rely on _check_exit_reached and base movement
                # Set direction towards the exit center just in case
                if self.target_exit_center:
                     dx_final = self.target_exit_center[0] - self.position[0]
                     dy_final = self.target_exit_center[1] - self.position[1]
                     if dx_final != 0 or dy_final != 0:
                           self.direction = math.atan2(dy_final, dx_final)
                self.target_speed = self.emergency_speed # Keep moving
            else:
                 # Set direction towards the *next* waypoint
                 next_target_x, next_target_y = self.path[0]
                 dx_next = next_target_x - self.position[0]
                 dy_next = next_target_y - self.position[1]
                 if dx_next != 0 or dy_next != 0:
                      self.direction = math.atan2(dy_next, dx_next)
                 self.target_speed = self.emergency_speed

        elif dist_to_waypoint > 0:
            # Still moving towards the current waypoint
            self.direction = math.atan2(dy, dx)
            self.target_speed = self.emergency_speed

        # The actual movement, considering collisions, is handled by super().move_continuous(dt) called after this


    def _check_steal_weapon(self):
        """Attempt to steal weapon from nearby armed adult."""
        # Don't attempt if already armed or a shooter or in emergency
        if self.has_weapon or self.is_shooter or self.in_emergency:
            return

        steal_range_sq = config.STEAL_RANGE ** 2
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, config.STEAL_RANGE)

        for agent in nearby_agents:
            # Check if agent is an adult, still active, and has a weapon
            if (agent in self.model.schedule and
                    agent.agent_type == "adult" and
                    getattr(agent, 'has_weapon', False)):

                dist_squared = distance_squared(self.position, agent.position)
                if dist_squared < steal_range_sq:
                    # Check line of sight for the steal attempt
                    if self.has_line_of_sight(agent.position):
                        # Attempt steal based on probability
                        if random.random() < config.STEAL_PROBABILITY: # Using original config probability per step
                            agent.has_weapon = False # Adult loses weapon
                            self.has_weapon = True   # Student gains weapon
                            self.is_shooter = True   # Student becomes a shooter
                            self.model.active_shooters.add(self) # Add to model's shooter list
                            print(f"!!! Student {self.unique_id} stole weapon from Adult {agent.unique_id} and became a shooter!")
                            # Immediately stop normal behavior and potentially find target
                            self.path = []
                            self.in_emergency = False # No longer fleeing
                            self.shooter_start_time = self.model.simulation_time # Mark start time
                            self._find_new_target(self.model.simulation_time) # Try to find target immediately
                            break # Stop checking other agents after successful steal

    def _validate_locked_target(self, current_time):
        """Check if current shooter target is still valid."""
        if self.locked_target is None:
            return False

        # Check if target still exists in simulation
        if self.locked_target not in self.model.schedule:
            self.locked_target = None
            return False

        # Check distance (release if too far)
        dist_squared = distance_squared(self.position, self.locked_target.position)
        if dist_squared > self.target_release_distance ** 2:
            self.locked_target = None
            return False

        # Check pursuit time limit
        if current_time - self.target_lock_time > self.max_target_pursuit_time:
            print(f"Shooter {self.unique_id} giving up on target {self.locked_target.unique_id} due to pursuit time.")
            self.locked_target = None
            return False

        # Check line of sight
        has_sight = self.has_line_of_sight(self.locked_target.position)
        if has_sight:
            self.target_last_seen_time = current_time # Update last seen time
            return True
        else:
            # Lose target if out of sight for too long
            time_since_seen = current_time - self.target_last_seen_time
            if time_since_seen > self.max_target_lost_time:
                 print(f"Shooter {self.unique_id} lost sight of target {self.locked_target.unique_id} for too long.")
                 self.locked_target = None
                 return False
            # Target is still valid, just temporarily out of sight
            return True

    def _find_new_target(self, current_time):
        """Shooter finds a new target (closest visible student or adult)."""
        search_radius = self.target_lock_distance # Use lock distance for search
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, search_radius)
        visible_targets = []

        for agent in nearby_agents:
            # Check if agent is valid, not self, not another shooter (optional)
            if (agent != self and
                    agent in self.model.schedule and
                    agent.agent_type in ["student", "adult"] and
                    not getattr(agent, 'is_shooter', False)): # Don't target other shooters

                # Check line of sight
                if self.has_line_of_sight(agent.position):
                    dist_squared = distance_squared(self.position, agent.position)
                    # Check if within lock distance
                    if dist_squared <= self.target_lock_distance ** 2:
                        visible_targets.append((agent, dist_squared))

        if not visible_targets:
            self.locked_target = None # No targets found
            return

        # Target the closest visible agent
        visible_targets.sort(key=lambda x: x[1])
        self.locked_target = visible_targets[0][0]
        self.target_lock_time = current_time
        self.target_last_seen_time = current_time
        print(f"Shooter {self.unique_id} locked target: {self.locked_target.unique_id} ({self.locked_target.agent_type})")

    def _pursue_target(self, dt, current_time):
        """Shooter pursues and engages the locked target."""
        if self.locked_target is None or self.locked_target not in self.model.schedule:
            self.locked_target = None # Target removed or invalid
            return

        target_pos = self.locked_target.position
        dx = target_pos[0] - self.position[0]
        dy = target_pos[1] - self.position[1]
        distance_sq = dx * dx + dy * dy
        distance = math.sqrt(distance_sq)

        # Always calculate direction towards target
        if distance > 1e-6:
            target_angle = math.atan2(dy, dx)
            self.direction = target_angle # Face the target

        # Check line of sight
        has_sight = self.has_line_of_sight(target_pos)

        # Effective shooting range check
        effective_shooting_range = self.shooting_range * 0.95

        if distance > effective_shooting_range:
            # Move towards target if outside effective range
            self.target_speed = self.max_speed # Move at full speed

            # Basic obstacle maneuvering if no line of sight while pursuing
            if not has_sight:
                 self.direction += random.uniform(-math.pi / 6, math.pi / 6)
                 self.target_speed *= 0.8 # Slow down slightly when maneuvering blind

        else:
            # Within shooting range
            if has_sight:
                # Stop moving to shoot accurately
                self.target_speed = 0
                self.velocity = (0, 0) # Hard stop

                # Check shooting cooldown
                if current_time - self.last_shot_time >= self.shooting_interval:
                    self._shoot_at_target(self.locked_target, current_time)
            else:
                # In range but no LoS - try to reposition slightly
                self.target_speed = self.max_speed * 0.4 # Move slowly to find LoS
                perp_angle_offset = random.choice([-math.pi / 2, math.pi / 2])
                self.direction = (target_angle + perp_angle_offset) % (2 * math.pi)

        # Movement is handled by super().move_continuous(dt)

    def _shoot_at_target(self, target, current_time):
        """Shooter attempts to shoot the target."""
        if target not in self.model.schedule: # Final check if target still exists
            self.locked_target = None
            return

        # Final line of sight check before firing
        if not self.has_line_of_sight(target.position):
            return

        # Create shot visualization data
        shot_data = {
            'start_pos': self.position,
            'end_pos': target.position,
            'start_time': current_time
        }
        self.model.active_shots.append(shot_data)

        # Play sound effect via the model
        if hasattr(self.model, 'gunshot_sound') and self.model.gunshot_sound:
            self.model.gunshot_sound.play()

        # Determine hit based on probability
        if random.random() < self.hit_probability:
            print(f"HIT: Shooter {self.unique_id} hit target {target.unique_id} ({target.agent_type})")

            # Play kill sound via the model
            if hasattr(self.model, 'kill_sound') and self.model.kill_sound:
                self.model.kill_sound.play()

            # Remove the hit agent
            if self.locked_target == target:
                self.locked_target = None
            self.model.remove_agent(target, reason="died")
        else:
            pass # Missed shot

        # Reset shot timer
        self.last_shot_time = current_time


    def _search_behavior(self, dt, current_time):
        """Shooter behavior when no target is locked: move randomly."""
        # Check if stuck against a wall
        self._check_wall_stuck(dt)

        # Initialize search state if needed
        if self.search_start_time == 0:
            self.search_start_time = current_time
            self.search_direction_change_time = current_time
            self.direction = random.uniform(0, 2 * math.pi) # Start random direction

        # Change direction periodically OR if stuck
        change_interval = config.SHOOTER_SEARCH_DURATION
        if (current_time - self.search_direction_change_time > change_interval
            or self.wall_stuck_time > self.wall_stuck_threshold):

            self.direction = random.uniform(0, 2 * math.pi) # Pick a new random direction
            self.search_direction_change_time = current_time
            # Reset stuck timer if direction changed due to being stuck
            if self.wall_stuck_time > self.wall_stuck_threshold:
                 self.wall_stuck_time = 0
                 self.wall_stuck_position = self.position

        # Move at a moderate search speed
        self.target_speed = self.max_speed * 0.6
        # Movement handled by super().move_continuous(dt)


    def _check_wall_stuck(self, dt):
         """Track if the agent has been stuck in roughly the same position."""
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
