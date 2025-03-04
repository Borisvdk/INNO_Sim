import random

from agents.adultagent import AdultAgent
from agents.studentagent import StudentAgent


class SchoolModel:
    """Model klasse voor de school simulatie."""

    def __init__(self, n_students=50, n_adults=10, width=100, height=100, STUDENT=0, ADULT=1 ):
        self.num_students = n_students
        self.num_adults = n_adults
        self.width = width
        self.height = height
        self.running = True
        self.schedule = []  # Lijst van alle agenten

        # Maak student agenten
        for i in range(self.num_students):
            x = random.uniform(5, self.width - 5)  # Kleine marge
            y = random.uniform(5, self.height - 5)  # Kleine marge
            student = StudentAgent(i, self, (x, y), STUDENT)
            self.schedule.append(student)

        # Maak volwassen agenten
        for i in range(self.num_adults):
            x = random.uniform(5, self.width - 5)
            y = random.uniform(5, self.height - 5)
            adult = AdultAgent(i + self.num_students, self, (x, y), ADULT)
            self.schedule.append(adult)

    def step(self):
        """Voer één tijdstap uit in de simulatie."""
        # Activeer alle agenten in willekeurige volgorde
        random.shuffle(self.schedule)
        for agent in self.schedule:
            agent.step()