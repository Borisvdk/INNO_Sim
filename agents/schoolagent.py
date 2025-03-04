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
        self.max_speed = 100

        # Parameters voor menselijkere beweging
        self.velocity = (0.0, 0.0)
        self.direction = random.uniform(0, 2 * math.pi)  # Richting in radialen
        self.direction_change_prob = 0.05  # Kans om richting te veranderen per stap
        self.target_speed = random.uniform(0.02, self.max_speed)  # Doelsnelheid
        self.acceleration = 0.01  # Hoe snel agent versnelt/vertraagt
        self.path_time = random.uniform(5, 15)  # Hoelang agent dezelfde richting aanhoudt
        self.current_path_time = 0  # Teller voor huidige pad

    def move(self):
        """Beweeg de agent volgens huidige richting en snelheid."""
        # Kijk of we van richting moeten veranderen
        if random.random() < self.direction_change_prob:
            # Kleine aanpassing aan richting in plaats van volledig nieuwe richting
            self.direction += random.uniform(-0.5, 0.5)
            # Houd richting tussen 0 en 2π
            self.direction %= 2 * math.pi
            # Stel nieuwe doelsnelheid in
            self.target_speed = random.uniform(0.02, self.max_speed)

        # Bereken gewenste snelheid vector op basis van richting
        target_vx = self.target_speed * math.cos(self.direction)
        target_vy = self.target_speed * math.sin(self.direction)

        # Geleidelijke aanpassing van huidige snelheid naar doelsnelheid (inertie)
        current_vx, current_vy = self.velocity
        new_vx = current_vx + (target_vx - current_vx) * self.acceleration
        new_vy = current_vy + (target_vy - current_vy) * self.acceleration

        # Update snelheid
        self.velocity = (new_vx, new_vy)

        # Update positie
        new_x = self.position[0] + new_vx
        new_y = self.position[1] + new_vy

        # Zorg dat agenten binnen de grenzen blijven
        new_x = max(0, min(self.model.width, new_x))
        new_y = max(0, min(self.model.height, new_y))

        # Als we een grens hebben bereikt, draai de richting om
        if new_x <= 0 or new_x >= self.model.width:
            self.direction = math.pi - self.direction  # Spiegel horizontaal
            self.velocity = (-new_vx, new_vy)
        if new_y <= 0 or new_y >= self.model.height:
            self.direction = 2 * math.pi - self.direction  # Spiegel verticaal
            self.velocity = (new_vx, -new_vy)

        # Update positie
        self.position = (new_x, new_y)

    def move_continuous(self, dt):
        """Beweeg de agent volgens huidige richting en snelheid met delta tijd."""
        # Tijdsafhankelijke kans om van richting te veranderen
        self.current_path_time += dt
        if self.current_path_time >= self.path_time:
            # Tijd om richting te veranderen
            self.direction += random.uniform(-0.8, 0.8)
            self.direction %= 2 * math.pi
            self.target_speed = random.uniform(0.02, self.max_speed)
            self.current_path_time = 0
            self.path_time = random.uniform(5, 15)  # Nieuwe pad-tijd

        # Bereken gewenste snelheid vector op basis van richting
        target_vx = self.target_speed * math.cos(self.direction)
        target_vy = self.target_speed * math.sin(self.direction)

        # Geleidelijke aanpassing van huidige snelheid naar doelsnelheid (inertie)
        current_vx, current_vy = self.velocity
        new_vx = current_vx + (target_vx - current_vx) * self.acceleration * dt * 5
        new_vy = current_vy + (target_vy - current_vy) * self.acceleration * dt * 5

        # Update snelheid
        self.velocity = (new_vx, new_vy)

        # Update positie met delta tijd
        new_x = self.position[0] + new_vx * dt
        new_y = self.position[1] + new_vy * dt

        # Zorg dat agenten binnen de grenzen blijven
        if new_x <= 0 or new_x >= self.model.width:
            self.direction = math.pi - self.direction  # Spiegel horizontaal
            self.velocity = (-new_vx, new_vy)
            # Corrigeer positie
            new_x = max(0, min(self.model.width, new_x))

        if new_y <= 0 or new_y >= self.model.height:
            self.direction = 2 * math.pi - self.direction  # Spiegel verticaal
            self.velocity = (new_vx, -new_vy)
            # Corrigeer positie
            new_y = max(0, min(self.model.height, new_y))

        # Update positie
        self.position = (new_x, new_y)

    def step(self):
        """Voer de acties uit voor deze tijdstap."""
        self.move()

    def step_continuous(self, dt):
        """Voer de acties uit voor een continue tijdstap met delta tijd dt."""
        self.move_continuous(dt)