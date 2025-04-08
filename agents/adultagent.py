from agents.schoolagent import SchoolAgent
import random
import math
from utilities import has_line_of_sight


class AdultAgent(SchoolAgent):
    """Agent class for adults (teachers, staff) with response behaviors for active shooters."""

    def __init__(self, unique_id, model, position, agent_type):
        # Call parent class constructor
        super().__init__(unique_id, model, agent_type, position)

        # Adult-specific attributes
        self.response_delay = random.randint(2, 5)  # 2-5 time steps delay
        self.color = (255, 0, 0)  # Red as default color

        # Shooter response attributes
        self.aware_of_shooter = False
        self.awareness_time = 0
        self.locked_target = None
        self.target_lock_time = 0
        self.target_last_seen_time = 0

        # Response capabilities
        self.max_response_distance = 100.0
        self.shooting_range = 25.0  # Same as student shooters
        self.last_shot_time = 0.0
        self.shooting_interval = 1.5  # Slightly faster than student shooters
        self.hit_probability = 0.8  # Better accuracy than student shooters

        # Navigation parameters
        self.target_acquisition_range = 150.0
        self.max_target_pursuit_time = 15.0  # Adults pursue longer
        self.max_target_lost_time = 3.0  # Adults remember targets longer

        # Alert and coordination state
        self.has_alerted_others = False

    def step_continuous(self, dt):
        """Adult step function with shooter response logic."""
        current_time = self.model.simulation_time

        # Check for active shooters
        if self.model.has_active_shooter and not self.aware_of_shooter:
            self._check_shooter_awareness(current_time)

        # If aware of shooter and armed, respond
        if self.aware_of_shooter and self.has_weapon:
            # Check if response delay has passed
            if current_time - self.awareness_time >= self.response_delay:
                # Alert others if not done yet
                if not self.has_alerted_others:
                    self._alert_nearby_adults()
                    self.has_alerted_others = True

                # Active shooter response
                self._shooter_response(dt, current_time)
        # If aware but not armed, notify other about the shooter
        elif self.aware_of_shooter and not self.has_weapon:
            # Notify other adults about the shooter
            if not self.has_alerted_others:
                self._alert_nearby_adults()
                self.has_alerted_others = True
                print(f"Adult {self.unique_id} alerted others about shooter")

            # Move away from the shooter
            self.target_speed = self.max_speed * 0.5  # Move cautiously
            super().move_continuous(dt)  # Call parent move function
        elif self.aware_of_shooter and current_time - self.awareness_time < self.response_delay:
            # Wait for response delay to pass before acting
            pass
        else:
            # Regular movement if not responding to shooter
            super().move_continuous(dt)

    def _check_shooter_awareness(self, current_time):
        """Check if adult becomes aware of shooter through direct observation or alerts."""
        # Check for direct observation of shooters
        for shooter in self.model.active_shooters:
            if shooter in self.model.schedule:
                # Calculate squared distance
                dx = shooter.position[0] - self.position[0]
                dy = shooter.position[1] - self.position[1]
                dist_squared = dx * dx + dy * dy

                # Check if shooter is within visible range and has line of sight
                if dist_squared < self.target_acquisition_range ** 2:
                    if has_line_of_sight(self.position, shooter.position, self.model.walls):
                        self.aware_of_shooter = True
                        self.awareness_time = current_time
                        print(f"Adult {self.unique_id} spotted shooter {shooter.unique_id}")
                        return

        # Check for gunshots heard (simplified - could be enhanced)
        for shot in self.model.active_shots:
            shot_time = shot['start_time']
            # Only consider recent shots
            if current_time - shot_time < 2.0:  # 2 second window to hear shots
                # Calculate distance to shot
                shot_x, shot_y = shot['start_pos']
                dx = shot_x - self.position[0]
                dy = shot_y - self.position[1]
                dist_squared = dx * dx + dy * dy

                # Gunshots can be heard from further away
                if dist_squared < (self.target_acquisition_range * 1.5) ** 2:
                    self.aware_of_shooter = True
                    self.awareness_time = current_time
                    print(f"Adult {self.unique_id} heard gunshots")
                    return

    def _alert_nearby_adults(self):
        """Alert other nearby adults about the shooter."""
        alert_radius = 50.0  # Alert radius
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, alert_radius)

        for agent in nearby_agents:
            if (agent != self and agent in self.model.schedule and
                    agent.agent_type == "adult" and not getattr(agent, "aware_of_shooter", False)):
                # Check if can communicate (line of sight)
                if has_line_of_sight(self.position, agent.position, self.model.walls):
                    agent.aware_of_shooter = True
                    agent.awareness_time = self.model.simulation_time
                    print(f"Adult {self.unique_id} alerted adult {agent.unique_id}")

    def _shooter_response(self, dt, current_time):
        """Respond to active shooter - target acquisition and engagement."""
        # Validate current target if exists
        target_is_valid = self._validate_locked_target(current_time)

        # Find new target if needed
        if not target_is_valid:
            self._find_shooter_target(current_time)

        # Pursue and engage target if exists
        if self.locked_target is not None:
            self._pursue_shooter(dt, current_time)
        else:
            # Search behavior if no target
            self._search_for_shooter(dt)

        # Use the base class movement with our modified direction and speed
        super().move_continuous(dt)

    def _validate_locked_target(self, current_time):
        """Check if current target is still valid."""
        if self.locked_target is None:
            return False

        # Check if target still exists in simulation
        if self.locked_target not in self.model.schedule:
            self.locked_target = None
            return False

        # Check if target is still a shooter
        if not getattr(self.locked_target, "is_shooter", False):
            self.locked_target = None
            return False

        # Check distance
        dx = self.locked_target.position[0] - self.position[0]
        dy = self.locked_target.position[1] - self.position[1]
        distance_squared = dx * dx + dy * dy

        if distance_squared > self.max_response_distance ** 2:
            self.locked_target = None
            return False

        # Check pursuit time
        if current_time - self.target_lock_time > self.max_target_pursuit_time:
            self.locked_target = None
            return False

        # Check line of sight
        has_sight = has_line_of_sight(self.position, self.locked_target.position, self.model.walls)
        if has_sight:
            self.target_last_seen_time = current_time
            return True
        else:
            # Check if we've lost sight for too long
            time_since_seen = current_time - self.target_last_seen_time
            if time_since_seen > self.max_target_lost_time:
                self.locked_target = None
                return False
            return True  # Still valid but temporarily lost sight

    def _find_shooter_target(self, current_time):
        """Find an active shooter to target."""
        search_radius = self.target_acquisition_range
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, search_radius)

        visible_shooters = []
        for agent in nearby_agents:
            # Check if agent is a shooter and still in the simulation
            if (agent in self.model.schedule and
                    getattr(agent, "is_shooter", False) and
                    has_line_of_sight(self.position, agent.position, self.model.walls)):
                # Calculate distance squared
                dx = self.position[0] - agent.position[0]
                dy = self.position[1] - agent.position[1]
                dist_squared = dx * dx + dy * dy

                visible_shooters.append((agent, dist_squared))

        if not visible_shooters:
            return

        # Target closest shooter
        visible_shooters.sort(key=lambda x: x[1])
        self.locked_target = visible_shooters[0][0]
        self.target_lock_time = current_time
        self.target_last_seen_time = current_time
        print(f"Adult {self.unique_id} targeting shooter {self.locked_target.unique_id}")

    def _pursue_shooter(self, dt, current_time):
        """Pursue and engage the targeted shooter."""
        if self.locked_target is None or self.locked_target not in self.model.schedule:
            return

        target_x, target_y = self.locked_target.position
        dx = target_x - self.position[0]
        dy = target_y - self.position[1]
        distance = math.sqrt(dx * dx + dy * dy)

        # Always calculate direction to target
        target_angle = math.atan2(dy, dx)

        # Check line of sight
        has_sight = has_line_of_sight(self.position, self.locked_target.position, self.model.walls)

        if distance > self.shooting_range:
            # Move toward target
            self.direction = target_angle
            self.target_speed = self.max_speed * 0.8  # Move cautiously

            # Take cover if no line of sight
            if not has_sight:
                # Try to move to get a better view
                self.direction += random.uniform(-math.pi / 4, math.pi / 4)
                self.target_speed *= 0.7  # Move more cautiously when can't see target
        else:
            # In shooting range - take cover and shoot if possible
            if has_sight:
                # Stop to stabilize shooting
                self.target_speed = 0
                self.velocity = (0, 0)

                # Shoot if cooldown expired
                if current_time - self.last_shot_time >= self.shooting_interval:
                    self._shoot_at_shooter(current_time)
            else:
                # No line of sight but in range - try to reposition
                perp_angle = target_angle + (math.pi / 2)
                self.direction = random.choice([perp_angle, perp_angle - math.pi]) % (2 * math.pi)
                self.target_speed = self.max_speed * 0.5

    def _shoot_at_shooter(self, current_time):
        """Shoot at the targeted shooter."""
        if self.locked_target is None or self.locked_target not in self.model.schedule:
            return

        # Double-check line of sight before shooting
        if not has_line_of_sight(self.position, self.locked_target.position, self.model.walls):
            return

        # Create shot visualization
        shot = {
            'start_pos': self.position,
            'end_pos': self.locked_target.position,
            'start_time': current_time
        }
        self.model.active_shots.append(shot)

        # Play sound if available
        if hasattr(self.model, 'gunshot_sound') and self.model.gunshot_sound:
            self.model.gunshot_sound.play()

        # Determine if shot hits
        if random.random() < self.hit_probability:
            print(f"Adult {self.unique_id} neutralized shooter {self.locked_target.unique_id}")

            # Play kill sound if available
            if hasattr(self.model, 'kill_sound') and self.model.kill_sound:
                self.model.kill_sound.play()

            # Remove the shooter
            target = self.locked_target
            self.locked_target = None  # Clear target before removal

            # Critical: handle active_shooters set in the model
            if target in self.model.active_shooters:
                self.model.active_shooters.remove(target)

            self.model.remove_agent(target, reason="died")
        else:
            print(f"Adult {self.unique_id} missed shot at shooter {self.locked_target.unique_id}")

        self.last_shot_time = current_time

    def _search_for_shooter(self, dt):
        """Search behavior when no target is locked but aware of shooter presence."""
        # Simple search pattern - just move in a somewhat random direction
        if random.random() < 0.05:  # Occasionally change direction
            self.direction = random.uniform(0, 2 * math.pi)

        self.target_speed = self.max_speed * 0.6  # Move at moderate speed while searching