from agents.schoolagent import SchoolAgent
import random
import math
from utilities import has_line_of_sight


class AdultAgent(SchoolAgent):
    """Agent class for adults (teachers, staff) with response behaviors for active shooters."""

    def __init__(self, unique_id, model, position, agent_type):
        """
        Initialize an AdultAgent.

        Args:
            unique_id: A unique identifier for the agent.
            model: The model instance the agent belongs to.
            position: The initial (x, y) position of the agent.
            agent_type: The type of agent (should be "adult").
        """
        super().__init__(unique_id, model, agent_type, position)

        self.response_delay = random.randint(2, 5)
        self.color = (255, 0, 0)

        self.aware_of_shooter = False
        self.awareness_time = 0
        self.locked_target = None
        self.target_lock_time = 0
        self.target_last_seen_time = 0

        self.max_response_distance = 100.0
        self.shooting_range = 25.0
        self.last_shot_time = 0.0
        self.shooting_interval = 1.5
        self.hit_probability = 0.8

        self.target_acquisition_range = 150.0
        self.max_target_pursuit_time = 15.0
        self.max_target_lost_time = 3.0

        self.has_alerted_others = False

    def step_continuous(self, dt):
        """
        Perform one time step for the adult agent, handling shooter awareness and response.

        Args:
            dt: The time step duration.
        """
        current_time = self.model.simulation_time

        if self.model.has_active_shooter and not self.aware_of_shooter:
            self._check_shooter_awareness(current_time)

        if self.aware_of_shooter and self.has_weapon:
            if current_time - self.awareness_time >= self.response_delay:
                if not self.has_alerted_others:
                    # Initiate communication: Alert nearby adults. (Doing by Talking)
                    self._alert_nearby_adults()
                    self.has_alerted_others = True

                self._shooter_response(dt, current_time)
        elif self.aware_of_shooter and not self.has_weapon:
            if not self.has_alerted_others:
                 # Initiate communication: Alert nearby adults even if unarmed. (Doing by Talking)
                self._alert_nearby_adults()
                self.has_alerted_others = True
                print(f"Adult {self.unique_id} alerted others about shooter")

            self.target_speed = self.max_speed * 0.5
            super().move_continuous(dt)
        elif self.aware_of_shooter and current_time - self.awareness_time < self.response_delay:
            pass
        else:
            super().move_continuous(dt)

    def _check_shooter_awareness(self, current_time):
        """
        Check if the adult becomes aware of a shooter via sight or sound.

        Args:
            current_time: The current simulation time.
        """
        for shooter in self.model.active_shooters:
            if shooter in self.model.schedule:
                dx = shooter.position[0] - self.position[0]
                dy = shooter.position[1] - self.position[1]
                dist_squared = dx * dx + dy * dy

                if dist_squared < self.target_acquisition_range ** 2:
                    if has_line_of_sight(self.position, shooter.position, self.model.walls):
                        self.aware_of_shooter = True
                        self.awareness_time = current_time
                        print(f"Adult {self.unique_id} spotted shooter {shooter.unique_id}")
                        return

        for shot in self.model.active_shots:
            shot_time = shot['start_time']
            if current_time - shot_time < 2.0:
                shot_x, shot_y = shot['start_pos']
                dx = shot_x - self.position[0]
                dy = shot_y - self.position[1]
                dist_squared = dx * dx + dy * dy

                if dist_squared < (self.target_acquisition_range * 1.5) ** 2:
                    self.aware_of_shooter = True
                    self.awareness_time = current_time
                    print(f"Adult {self.unique_id} heard gunshots")
                    return

    def _alert_nearby_adults(self):
        """
        Alert other nearby adults about the shooter if line of sight exists.
        This implements the "Doing by Talking" concept: the act of alerting causes others to become aware.
        """
        alert_radius = 50.0
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, alert_radius)

        for agent in nearby_agents:
            if (agent != self and agent in self.model.schedule and
                    agent.agent_type == "adult" and not getattr(agent, "aware_of_shooter", False)):
                if has_line_of_sight(self.position, agent.position, self.model.walls):
                    # Talking (alerting) causes Doing (setting awareness in the other agent).
                    agent.aware_of_shooter = True
                    agent.awareness_time = self.model.simulation_time
                    print(f"Adult {self.unique_id} alerted adult {agent.unique_id}")

    def _shooter_response(self, dt, current_time):
        """
        Manage the adult's response to an active shooter, including target acquisition and engagement.

        Args:
            dt: The time step duration.
            current_time: The current simulation time.
        """
        target_is_valid = self._validate_locked_target(current_time)

        if not target_is_valid:
            self._find_shooter_target(current_time)

        if self.locked_target is not None:
            self._pursue_shooter(dt, current_time)
        else:
            self._search_for_shooter(dt)

        super().move_continuous(dt)

    def _validate_locked_target(self, current_time):
        """
        Check if the currently locked target is still valid (exists, is a shooter, within range, etc.).

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

        if not getattr(self.locked_target, "is_shooter", False):
            self.locked_target = None
            return False

        dx = self.locked_target.position[0] - self.position[0]
        dy = self.locked_target.position[1] - self.position[1]
        distance_squared = dx * dx + dy * dy

        if distance_squared > self.max_response_distance ** 2:
            self.locked_target = None
            return False

        if current_time - self.target_lock_time > self.max_target_pursuit_time:
            self.locked_target = None
            return False

        has_sight = has_line_of_sight(self.position, self.locked_target.position, self.model.walls)
        if has_sight:
            self.target_last_seen_time = current_time
            return True
        else:
            time_since_seen = current_time - self.target_last_seen_time
            if time_since_seen > self.max_target_lost_time:
                self.locked_target = None
                return False
            return True

    def _find_shooter_target(self, current_time):
        """
        Find the closest visible active shooter within the acquisition range.

        Args:
            current_time: The current simulation time.
        """
        search_radius = self.target_acquisition_range
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, search_radius)

        visible_shooters = []
        for agent in nearby_agents:
            if (agent in self.model.schedule and
                    getattr(agent, "is_shooter", False) and
                    has_line_of_sight(self.position, agent.position, self.model.walls)):
                dx = self.position[0] - agent.position[0]
                dy = self.position[1] - agent.position[1]
                dist_squared = dx * dx + dy * dy

                visible_shooters.append((agent, dist_squared))

        if not visible_shooters:
            return

        visible_shooters.sort(key=lambda x: x[1])
        self.locked_target = visible_shooters[0][0]
        self.target_lock_time = current_time
        self.target_last_seen_time = current_time
        print(f"Adult {self.unique_id} targeting shooter {self.locked_target.unique_id}")

    def _pursue_shooter(self, dt, current_time):
        """
        Move towards the locked shooter target and attempt to engage if in range and sight.

        Args:
            dt: The time step duration.
            current_time: The current simulation time.
        """
        if self.locked_target is None or self.locked_target not in self.model.schedule:
            return

        target_x, target_y = self.locked_target.position
        dx = target_x - self.position[0]
        dy = target_y - self.position[1]
        distance = math.sqrt(dx * dx + dy * dy)

        target_angle = math.atan2(dy, dx)

        has_sight = has_line_of_sight(self.position, self.locked_target.position, self.model.walls)

        if distance > self.shooting_range:
            self.direction = target_angle
            self.target_speed = self.max_speed * 0.8

            if not has_sight:
                self.direction += random.uniform(-math.pi / 4, math.pi / 4)
                self.target_speed *= 0.7
        else:
            if has_sight:
                self.target_speed = 0
                self.velocity = (0, 0)

                if current_time - self.last_shot_time >= self.shooting_interval:
                    self._shoot_at_shooter(current_time)
            else:
                perp_angle = target_angle + (math.pi / 2)
                self.direction = random.choice([perp_angle, perp_angle - math.pi]) % (2 * math.pi)
                self.target_speed = self.max_speed * 0.5

    def _shoot_at_shooter(self, current_time):
        """
        Attempt to shoot the locked target if line of sight is confirmed.

        Args:
            current_time: The current simulation time.
        """
        if self.locked_target is None or self.locked_target not in self.model.schedule:
            return

        if not has_line_of_sight(self.position, self.locked_target.position, self.model.walls):
            return

        shot = {
            'start_pos': self.position,
            'end_pos': self.locked_target.position,
            'start_time': current_time
        }
        self.model.active_shots.append(shot)

        if hasattr(self.model, 'gunshot_sound') and self.model.gunshot_sound:
            self.model.gunshot_sound.play()

        if random.random() < self.hit_probability:
            print(f"Adult {self.unique_id} neutralized shooter {self.locked_target.unique_id}")

            if hasattr(self.model, 'kill_sound') and self.model.kill_sound:
                self.model.kill_sound.play()

            target = self.locked_target
            self.locked_target = None

            if target in self.model.active_shooters:
                self.model.active_shooters.remove(target)

            self.model.remove_agent(target, reason="died")
        else:
            print(f"Adult {self.unique_id} missed shot at shooter {self.locked_target.unique_id}")

        self.last_shot_time = current_time

    def _search_for_shooter(self, dt):
        """
        Define movement behavior when the agent is aware but has no locked target.

        Args:
            dt: The time step duration.
        """
        if random.random() < 0.05:
            self.direction = random.uniform(0, 2 * math.pi)

        self.target_speed = self.max_speed * 0.6