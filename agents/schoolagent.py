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
        self.max_speed = 100.0

        # Parameters voor menselijkere beweging
        self.velocity = (0.0, 0.0)
        self.direction = random.uniform(0, 2 * math.pi)  # Richting in radialen
        self.direction_change_prob = 0.05  # Kans om richting te veranderen per stap
        self.target_speed = random.uniform(0.75 * self.max_speed, self.max_speed)  # Doelsnelheid
        self.acceleration = 0.5  # Hoe snel agent versnelt/vertraagt

        # Tijdgebaseerde richtingsverandering - langere periodes
        self.path_time = random.uniform(10, 30)  # VERHOOGD: veel langere loopperiodes (10-30 sec)
        self.current_path_time = 0  # Teller voor huidige pad

        # Parameters voor stilstand - langere periodes
        self.is_idle = False
        self.idle_prob = 0.4  # Kans om stil te gaan staan bij richtingverandering
        self.idle_time = 0  # Huidige tijd dat agent stil staat
        self.idle_duration = random.uniform(8, 20)  # VERHOOGD: veel langere stilstandperiodes (8-20 sec)

        # Volwassenen staan vaker en langer stil dan studenten
        if agent_type == 1:  # ADULT
            self.idle_prob = 0.6  # 60% kans om stil te staan bij richtingverandering
            self.idle_duration = random.uniform(15, 40)  # VERHOOGD: 15-40 seconden stilstand
            self.path_time = random.uniform(15, 40)  # VERHOOGD: 15-40 seconden doorlopen

    def move(self):
        """Beweeg de agent volgens huidige richting en snelheid."""
        # Als agent stilstaat, doe niets
        if self.is_idle:
            # Discreter tijdsverloop voor idle tijd in niet-continuous mode
            self.idle_time += 1
            if self.idle_time >= self.idle_duration:
                self.is_idle = False
                self.direction = random.uniform(0, 2 * math.pi)
                self.target_speed = random.uniform(0.5, self.max_speed)
            return

        # Bepalen of we van richting veranderen (tijdsgebaseerd)
        self.current_path_time += 1
        if self.current_path_time >= self.path_time:
            # Reset pad timer
            self.current_path_time = 0
            self.path_time = random.uniform(10, 30)
            if self.agent_type == 1:
                self.path_time = random.uniform(15, 40)

            # Verander richting
            self.direction += random.uniform(-1.0, 1.0)
            self.direction %= 2 * math.pi
            self.target_speed = random.uniform(0.5, self.max_speed)

            # Bepaal of agent stil gaat staan
            if random.random() < self.idle_prob:
                self.is_idle = True
                self.velocity = (0, 0)
                self.idle_time = 0
                self.idle_duration = random.uniform(8, 20)
                if self.agent_type == 1:  # ADULT
                    self.idle_duration = random.uniform(15, 40)
                return

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

        # **Controleer of agent buiten de grenzen gaat**
        if new_x < 0 or new_x > self.model.width or new_y < 0 or new_y > self.model.height:
            self.model.remove_agent(self)  # Verwijder agent uit de simulatie
            return  # Stop de functie zodat de positie niet meer wordt geüpdatet

        # Update positie
        self.position = (new_x, new_y)

    def move_continuous(self, dt):
        """Beweeg de agent volgens huidige richting en snelheid met delta tijd."""
        # Als agent stilstaat, update idle time
        if self.is_idle:
            self.idle_time += dt
            if self.idle_time >= self.idle_duration:
                # Stilstandperiode is voorbij
                self.is_idle = False
                # Kies een nieuwe richting en snelheid
                self.direction = random.uniform(0, 2 * math.pi)
                self.target_speed = random.uniform(0.5, self.max_speed)
                self.current_path_time = 0
            return

        # Tijdsafhankelijke kans om van richting te veranderen
        self.current_path_time += dt
        if self.current_path_time >= self.path_time:
            # Reset pad timer
            self.current_path_time = 0
            self.path_time = random.uniform(10, 30)
            if self.agent_type == 1:
                self.path_time = random.uniform(15, 40)

            # Verander richting
            self.direction += random.uniform(-1.0, 1.0)
            self.direction %= 2 * math.pi
            self.target_speed = random.uniform(0.5, self.max_speed)

            # Kijk of we nu gaan stilstaan
            if random.random() < self.idle_prob:
                self.is_idle = True
                self.velocity = (0, 0)
                self.idle_time = 0
                # Reset idle duur voor variatie bij elke stilstand
                self.idle_duration = random.uniform(8, 20)
                if self.agent_type == 1:  # ADULT
                    self.idle_duration = random.uniform(15, 40)
                return

        # Bereken snelheid op basis van richting
        target_vx = self.target_speed * math.cos(self.direction)
        target_vy = self.target_speed * math.sin(self.direction)

        # Geleidelijke snelheidsovergang
        current_vx, current_vy = self.velocity
        new_vx = current_vx + (target_vx - current_vx) * self.acceleration * dt * 5
        new_vy = current_vy + (target_vy - current_vy) * self.acceleration * dt * 5

        # Update snelheid
        self.velocity = (new_vx, new_vy)

        # Update positie
        new_x = self.position[0] + new_vx * dt
        new_y = self.position[1] + new_vy * dt

        # **Controleer of agent buiten de grenzen gaat**
        if new_x < 0 or new_x > self.model.width or new_y < 0 or new_y > self.model.height:
            self.model.remove_agent(self)  # Verwijder agent
            return  # Stop verdere updates

        # Update positie
        self.position = (new_x, new_y)

    def step(self):
        """Voer de acties uit voor deze tijdstap."""
        self.move()

    def step_continuous(self, dt):
        """Voer de acties uit voor een continue tijdstap met delta tijd dt."""
        self.move_continuous(dt)