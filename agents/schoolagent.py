import random
import math


class SchoolAgent:
    """Basis agent klasse voor alle agenten in de school simulatie."""

    def __init__(self, unique_id, model, agent_type, position):
        self.unique_id = unique_id
        self.model = model
        self.agent_type = agent_type  # STUDENT of ADULT
        self.position = position
        self.has_weapon = False
        self.awareness = 0.0
        self.max_speed = 200

        # Parameters voor menselijkere beweging
        self.velocity = (0.0, 0.0)
        self.direction = random.uniform(0, 2 * math.pi)  # Richting in radialen
        self.direction_change_prob = 0.05  # Kans om richting te veranderen per stap
        self.target_speed = random.uniform(0.75 * self.max_speed, self.max_speed)  # Doelsnelheid
        self.acceleration = 0.5  # Hoe snel agent versnelt/vertraagt
        self.path_time = random.uniform(5, 15)  # Hoelang agent dezelfde richting aanhoudt
        self.current_path_time = 0  # Teller voor huidige pad

    def move_continuous(self, dt):
        """Beweeg de agent volgens huidige richting en snelheid met delta tijd."""
        self.current_path_time += dt
        if self.current_path_time >= self.path_time:
            self.direction += random.uniform(-0.8, 0.8)
            self.direction %= 2 * math.pi
            self.target_speed = random.uniform(0.02, self.max_speed)
            self.current_path_time = 0
            self.path_time = random.uniform(5, 15)

        # Bereken snelheid op basis van richting
        target_vx = self.target_speed * math.cos(self.direction)
        target_vy = self.target_speed * math.sin(self.direction)

        # Geleidelijke snelheidsovergang
        current_vx, current_vy = self.velocity
        new_vx = current_vx + (target_vx - current_vx) * self.acceleration * dt * 5
        new_vy = current_vy + (target_vy - current_vy) * self.acceleration * dt * 5

        # Update snelheid
        self.velocity = (new_vx, new_vy)

        # Nieuwe potentiële positie
        new_x = self.position[0] + new_vx * dt
        new_y = self.position[1] + new_vy * dt

        if self.agent_type == "student":
            # Studenten kunnen de simulatie verlaten
            if new_x < 0 or new_x > self.model.width or new_y < 0 or new_y > self.model.height:
                self.model.remove_agent(self)  # Verwijder student uit simulatie
                return  # Stop verdere updates
        else:
            # Volwassenen mogen de grenzen niet overschrijden
            new_x = max(0, min(new_x, self.model.width))
            new_y = max(0, min(new_y, self.model.height))

        # Update positie
        self.position = (new_x, new_y)

    def step(self):
        """Voer de acties uit voor deze tijdstap."""
        self.move()

    def step_continuous(self, dt):
        """Voer de acties uit voor een continue tijdstap met delta tijd dt."""
        self.move_continuous(dt)
