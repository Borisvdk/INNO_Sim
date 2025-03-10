import random
import math


class SchoolAgent:
    """Basis agent klasse voor alle agenten in de school simulatie."""

    def __init__(self, unique_id, model, agent_type, position, agents):
        self.unique_id = unique_id
        self.model = model
        self.agent_type = agent_type  # STUDENT of ADULT
        self.position = position
        self.has_weapon = False
        self.awareness = 0.0
        self.agents = agents

        # Aangepaste snelheid voor grotere school
        self.max_speed = 100.0

        # Parameters voor menselijkere beweging
        self.velocity = (0.0, 0.0)
        self.direction = random.uniform(0, 2 * math.pi)  # Richting in radialen
        self.target_speed = random.uniform(0.75 * self.max_speed, self.max_speed)  # Doelsnelheid
        self.acceleration = 0.5  # Hoe snel agent versnelt/vertraagt

        # Richtingsverandering & stilstand parameters
        self.path_time = random.uniform(0.5, 2)
        self.current_path_time = 0
        self.is_idle = False
        self.idle_prob = 0.5  
        self.idle_time = 0  
        self.idle_duration = random.uniform(1, 3)  

        if agent_type == 1:  # ADULT
            self.idle_prob = 0.7  
            self.idle_duration = random.uniform(1.5, 4)  
            self.path_time = random.uniform(1, 3)  

        # **Proximity check timer**
        self.proximity_timer = 0.0  # Keeps track of time since last check
        self.proximity_check_interval = 1

    def move_continuous(self, dt):
        """Beweeg de agent volgens huidige richting en snelheid met delta tijd."""
        if self.is_idle:
            self.idle_time += dt
            if self.idle_time >= self.idle_duration:
                self.is_idle = False
                self.direction = random.uniform(0, 2 * math.pi)
                self.target_speed = random.uniform(0.5, self.max_speed)
                self.current_path_time = 0
            return

        self.current_path_time += dt
        if self.current_path_time >= self.path_time:
            self.current_path_time = 0
            self.path_time = random.uniform(0.5, 2)
            if self.agent_type == 1:
                self.path_time = random.uniform(1, 3)

            self.direction += random.uniform(-math.pi, math.pi)
            self.direction %= 2 * math.pi
            self.target_speed = random.uniform(0.5, self.max_speed)

            if random.random() < self.idle_prob:
                self.is_idle = True
                self.velocity = (0, 0)
                self.idle_time = 0
                self.idle_duration = random.uniform(1, 3)
                if self.agent_type == 1:
                    self.idle_duration = random.uniform(1.5, 4)
                return

        target_vx = self.target_speed * math.cos(self.direction)
        target_vy = self.target_speed * math.sin(self.direction)

        current_vx, current_vy = self.velocity
        new_vx = current_vx + (target_vx - current_vx) * self.acceleration * dt * 5
        new_vy = current_vy + (target_vy - current_vy) * self.acceleration * dt * 5

        self.velocity = (new_vx, new_vy)

        new_x = self.position[0] + new_vx * dt
        new_y = self.position[1] + new_vy * dt

        if self.agent_type == "student":
            if new_x < 0 or new_x > self.model.width or new_y < 0 or new_y > self.model.height:
                self.model.remove_agent(self)
                return  
        else:
            new_x = max(0, min(new_x, self.model.width))
            new_y = max(0, min(new_y, self.model.height))

        self.position = (new_x, new_y)

    def distance_to(self, other_agent):
        """Calculate distance to another agent"""
        return math.sqrt((self.position[0] - other_agent.position[0]) ** 2 + (self.position[1] - other_agent.position[1]) ** 2)

    def check_proximity(self, radius):
        """Check which agents are within a given radius of each other"""
        for agent in self.agents:
            for other in self.agents:
                if agent != other:
                    dist = agent.distance_to(other)
                    if dist <= radius:
                        pass
                        print(f"{agent.unique_id} is within {radius} of {other.unique_id} (dist={dist:.2f})")

    def step_continuous(self, dt):
        """Voer de acties uit voor een continue tijdstap met delta tijd dt."""
        self.move_continuous(dt)

        # **Only check proximity if enough time has passed**
        self.proximity_timer += dt
        if self.proximity_timer >= self.proximity_check_interval:
            self.check_proximity(5)
            self.proximity_timer = 0  # Reset timer
