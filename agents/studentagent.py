# --- START OF FILE studentagent.py ---

import math
import random
import config
import pygame
from agents.schoolagent import SchoolAgent
from dijkstra_test import astar
from utilities import has_line_of_sight # Keep this, shooter still uses it

class StudentAgent(SchoolAgent):
    """Agent class for students with potential shooter behaviors."""

    def __init__(self, unique_id, model, position, agent_type):
        # Initialize parent class
        super().__init__(unique_id, model, agent_type, position)

        # Student-specific attributes
        self.fear_level = 0.0
        self.grab_weapon_prob = 0.05 # Note: This is defined but not used in step logic
        self.state = "Normal" # Consider removing if in_emergency covers it

        self.path = []
        # self.reached_exit = False # Redundant if agent is removed upon exit
        self.in_emergency = False
        self.normal_speed = random.uniform(40.0, 60.0)  # Speed for normal movement
        self.emergency_speed = random.uniform(60.0, 90.0) # Faster speed during emergency

        # Shooter-specific attributes (remains the same)
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

    # at_exit method is likely redundant now due to rect check, but keep if needed elsewhere
    # def at_exit(self):
    #    return self.position[0] <= 0 or self.position[0] >= SIM_WIDTH or self.position[1] <= 0 or self.position[1] >= SIM_HEIGHT

    def step_continuous(self, dt):
        """
        Handles student agent behavior: shooter, evacuation (awareness-based), or normal roaming.
        """
        # --- Shooter Timeout ---
        if self.is_shooter:
            # ... (shooter timeout logic remains the same) ...
            pass # Placeholder

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

            super().move_continuous(dt)


        # --- Non-Shooter Behavior ---
        else:
            # --- 1. Awareness Check (Only if not already fleeing) ---
            # Check if there's an active shooter and this student isn't already fleeing
            if not self.in_emergency and self.model.has_active_shooter:
                # Iterate through ALL active shooters in the model
                for shooter in self.model.active_shooters:
                    # Ensure shooter is still valid (might have been removed in the same step)
                    if shooter in self.model.schedule:
                        # ***** CHANGED LOGIC: Check proximity instead of LoS *****
                        # Calculate squared distance for efficiency
                        dx = shooter.position[0] - self.position[0]
                        dy = shooter.position[1] - self.position[1]
                        dist_squared = dx * dx + dy * dy

                        # Check if within awareness range (using squared distance)
                        if dist_squared < config.AWARENESS_RANGE ** 2:
                            print(f"Student {self.unique_id} detected shooter {shooter.unique_id} nearby (dist^2={dist_squared:.1f})! Entering emergency.")
                            self.in_emergency = True

                            # --- Calculate path to exit immediately ---
                            exit_x_start = 50 * (config.SIM_WIDTH / 60)
                            exit_x_end = 58 * (config.SIM_WIDTH / 60)
                            exit_y_start = 0
                            exit_y_end = 2 * (config.SIM_HEIGHT / 40) + 10
                            exit_center_target = ((exit_x_start + exit_x_end) / 2, exit_y_end / 2)

                            try:
                                path = astar((self.position[0], self.position[1]),
                                             exit_center_target,
                                             self.model.wall_rects) # Use pygame.Rect list
                                if path:
                                    self.path = path
                                    print(f"Student {self.unique_id} calculated path to exit.")
                                else:
                                    print(f"⚠️ No path found for student {self.unique_id} at {self.position} after detecting shooter.")
                                    # Optional: Add fallback behavior here
                            except Exception as e:
                                 print(f"Error during A* pathfinding for student {self.unique_id}: {e}")
                                 # Handle error gracefully

                            # Once awareness is triggered by *any* shooter, stop checking others
                            break # <-- Important! Stop checking other shooters
                        # **********************************************************

            # --- 2. Action Based on State ---
            # Define exit rect (needed for both states if checking collision)
            exit_x_start = 50 * (config.SIM_WIDTH / 60)
            exit_x_end = 58 * (config.SIM_WIDTH / 60)
            exit_y_start = 0
            exit_y_end = 2 * (config.SIM_HEIGHT / 40) + 10
            school_exit = pygame.Rect(exit_x_start, exit_y_start, exit_x_end - exit_x_start, exit_y_end - exit_y_start)
            exit_center_target = ((exit_x_start + exit_x_end) / 2, exit_y_end / 2)

            # --- Emergency Evacuation State (Fleeing) ---
            if self.in_emergency:
                # ... (Fleeing logic remains the same as before: check exit, follow path, move to center, avoid collisions) ...
                # 1. Check exit collision
                if school_exit.collidepoint(self.position):
                    self.model.remove_agent(self)
                    return # Agent removed

                # 2. Follow path
                if self.path:
                    target_x, target_y = self.path[0]
                    dx, dy = target_x - self.position[0], target_y - self.position[1]
                    dist = math.hypot(dx, dy)
                    move_speed = self.emergency_speed

                    if dt > 0 and dist < move_speed * dt:
                         self.position = (target_x, target_y)
                         self.path.pop(0)
                         self.model.spatial_grid.update_agent(self)
                    elif dist > 0:
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
                    if not self.path:
                         print(f"Student {self.unique_id} reached end of path, moving towards exit center.")

                # 3. Move towards exit center if no path
                else:
                    target_x, target_y = exit_center_target
                    dx, dy = target_x - self.position[0], target_y - self.position[1]
                    dist = math.hypot(dx, dy)
                    move_speed = self.emergency_speed * 0.75

                    if dist > self.radius:
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

                # 4. Simple collision avoidance for fleeing agents
                self._avoid_student_collisions()

            # --- Normal Roaming State ---
            else: # Not in emergency and not a shooter
                self._check_steal_weapon()
                super().move_continuous(dt)

    # ... (rest of the methods _check_steal_weapon, _avoid_student_collisions, _validate_locked_target, etc. remain unchanged) ...
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
            distance_sq = dx * dx + dy * dy # Use squared distance for efficiency
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
                self.model.active_shooters.add(self) # Add to model's set
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
        for other in self.model.schedule:
            # Check if other agent exists, is a student, and is not self
            if other != self and other in self.model.schedule and other.agent_type == "student":
                other_rect_size = other.radius * 2
                other_rect = pygame.Rect(
                    other.position[0] - other_rect_size / 2,
                    other.position[1] - other_rect_size / 2,
                    other_rect_size, other_rect_size
                )

                if student_rect.colliderect(other_rect):
                    # Apply a small random nudge
                    nudge_strength = 0.5 # Small nudge
                    old_pos = self.position
                    new_x = self.position[0] + random.uniform(-nudge_strength, nudge_strength)
                    new_y = self.position[1] + random.uniform(-nudge_strength, nudge_strength)

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
                        break # Apply only one nudge per step

        # No need to return nudged status unless used elsewhere

    # --- Shooter specific methods remain unchanged ---
    def _validate_locked_target(self, current_time):
       # ... (keep existing code) ...
       # Add check if target still in model.schedule
        if self.locked_target is None:
            return False
        if self.locked_target not in self.model.schedule:
            print(f"Shooter {self.unique_id} lost target {self.locked_target.unique_id} (removed)")
            self.locked_target = None
            return False
        # ... rest of validation ...
        target_x, target_y = self.locked_target.position
        dx = target_x - self.position[0]
        dy = target_y - self.position[1]
        distance_squared = dx * dx + dy * dy
        if distance_squared > self.target_release_distance * self.target_release_distance:
            #print(f"Shooter {self.unique_id} released target {self.locked_target.unique_id} (too far)")
            self.locked_target = None
            return False
        time_since_locked = current_time - self.target_lock_time
        if time_since_locked > self.max_target_pursuit_time:
            #print(f"Shooter {self.unique_id} switching targets after pursuing {self.locked_target.unique_id} too long")
            self.locked_target = None
            return False
        has_sight = self.has_line_of_sight(self.locked_target.position)
        if has_sight:
            self.target_last_seen_time = current_time
            return True
        else:
            time_since_last_seen = current_time - self.target_last_seen_time
            if time_since_last_seen > self.max_target_lost_time:
                #print(f"Shooter {self.unique_id} lost target {self.locked_target.unique_id} (out of sight)")
                self.locked_target = None
                return False
            else:
                return True # Still pursuing briefly

    def _find_new_target(self, current_time):
        # ... (keep existing code) ...
        search_radius = self.target_lock_distance
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, search_radius)
        visible_targets = []
        for agent in nearby_agents:
             # Check agent still exists and is valid target type
            if agent != self and agent in self.model.schedule and agent.agent_type in ["student", "adult"]:
                if self.has_line_of_sight(agent.position):
                    dx = self.position[0] - agent.position[0]
                    dy = self.position[1] - agent.position[1]
                    distance_squared = dx * dx + dy * dy
                    # Ensure distance is within lock distance BEFORE adding
                    if distance_squared <= search_radius * search_radius:
                         visible_targets.append((agent, distance_squared))

        if not visible_targets:
            return

        visible_targets.sort(key=lambda x: x[1])
        nearest_agent = visible_targets[0][0]
        # Final LoS check before locking
        if self.has_line_of_sight(nearest_agent.position):
            self.locked_target = nearest_agent
            self.target_lock_time = current_time
            self.target_last_seen_time = current_time
            # print(f"Shooter {self.unique_id} locked onto {self.locked_target.unique_id}")


    def _pursue_target(self, dt, current_time):
        # ... (keep existing code, ensure self.velocity is updated correctly) ...
        # Make sure this method sets self.velocity, which super().move_continuous will use
        target_x, target_y = self.locked_target.position
        dx = target_x - self.position[0]
        dy = target_y - self.position[1]
        distance = math.sqrt(dx * dx + dy * dy)
        has_sight = self.has_line_of_sight(self.locked_target.position)

        if distance > self.shooting_range:
            target_angle = math.atan2(dy, dx)
            if has_sight:
                # Move directly towards target
                self.velocity = (math.cos(target_angle) * self.max_speed, math.sin(target_angle) * self.max_speed)
                self.direction = target_angle # Update direction for potential use elsewhere
            else:
                 # Navigate around obstacles (simplified: use parent avoidance forces)
                 # Parent's move_continuous already includes wall/agent avoidance forces.
                 # We just need to maintain a general direction towards the target.
                 # Let's slightly adjust the direction but let parent forces handle avoidance.
                 self.direction = target_angle # Keep aiming towards target
                 # Velocity will be influenced by parent's force calculations in move_continuous
                 # Let's ensure target speed is set for parent method
                 self.target_speed = self.max_speed # Maintain high speed pursuit

                 # Wall stuck logic could be added here if parent avoidance isn't enough
                 # ... (wall stuck checks and direction changes) ...

        else: # In shooting range
            self.velocity = (0, 0) # Stop moving
            self.target_speed = 0 # Stop trying to move via parent logic

            if current_time - self.last_shot_time >= self.shooting_interval:
                if has_sight:
                    self._shoot_at_target(self.locked_target, current_time)
                # else: Cannot shoot, no LoS

    def _shoot_at_target(self, target, current_time):
        # ... (keep existing code) ...
        shot = {'start_pos': self.position, 'end_pos': target.position, 'start_time': current_time}
        self.model.active_shots.append(shot)
        if hasattr(self.model, 'gunshot_sound') and self.model.gunshot_sound:
            self.model.gunshot_sound.play()

        if random.random() < self.hit_probability:
            print(f"Shooter {self.unique_id} hit agent {target.unique_id}")
            if hasattr(self.model, 'kill_sound') and self.model.kill_sound:
                self.model.kill_sound.play()
            if self.locked_target == target:
                self.locked_target = None
            self.model.remove_agent(target) # Critical: Remove target
        else:
             # print(f"Shooter {self.unique_id} missed") # Reduce miss noise
             pass

        self.last_shot_time = current_time

    def search_behavior(self, dt):
        # ... (keep existing code, ensure self.velocity/target_speed is set) ...
        # Set target speed and direction for parent's move_continuous
        if not hasattr(self, 'search_start_time'): # Initialize if needed
            self.search_start_time = self.model.simulation_time
            self.search_direction_change_time = 0

        if self.model.simulation_time - self.search_direction_change_time > 2.0:
            self.direction = random.uniform(0, 2 * math.pi)
            self.search_direction_change_time = self.model.simulation_time

        self.target_speed = self.max_speed * 0.7 # Move slower while searching
        # Velocity will be calculated by parent's move_continuous based on direction and target_speed + forces
# --- END OF FILE studentagent.py ---