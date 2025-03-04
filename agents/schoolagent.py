import random


class SchoolAgent:
    """Basis agent klasse voor alle agenten in de school simulatie."""

    def __init__(self, unique_id, model, agent_type, position):
        self.unique_id = unique_id
        self.model = model
        self.agent_type = agent_type  # STUDENT of ADULT
        self.position = position
        self.has_weapon = False
        self.awareness = 0.0
        self.max_speed = 0.2  # Verlaagd voor betere visualisatie

    def move(self):
        """Beweeg de agent volgens willekeurige beweging."""
        # Genereer een willekeurige beweging
        dx = random.uniform(-self.max_speed, self.max_speed)
        dy = random.uniform(-self.max_speed, self.max_speed)

        # Bereken nieuwe positie
        new_x = self.position[0] + dx
        new_y = self.position[1] + dy

        # Zorg dat agenten binnen de grenzen blijven
        new_x = max(0, min(self.model.width, new_x))
        new_y = max(0, min(self.model.height, new_y))

        # Update positie
        self.position = (new_x, new_y)

    def step(self):
        """Voer de acties uit voor deze tijdstap."""
        self.move()
