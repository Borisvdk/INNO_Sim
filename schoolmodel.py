import math
import random

from agents.adultagent import AdultAgent
from agents.studentagent import StudentAgent


class SchoolModel:
    """Model klasse voor de school simulatie."""

    def __init__(self, n_students=50, n_adults=10, width=100, height=100):
        self.num_students = n_students
        self.num_adults = n_adults
        self.width = width
        self.height = height
        self.running = True
        self.schedule = []  # Lijst van alle agenten
        self.simulation_time = 0.0  # Totale gesimuleerde tijd

        # Maak student agenten
        for i in range(self.num_students):
            x = random.uniform(5, self.width - 5)  # Kleine marge
            y = random.uniform(5, self.height - 5)  # Kleine marge
            student = StudentAgent(i, self, (x, y), "student", self.schedule)
            self.schedule.append(student)

        # Maak volwassen agenten
        for i in range(self.num_adults):
            x = random.uniform(5, self.width - 5)
            y = random.uniform(5, self.height - 5)
            adult = AdultAgent(i + self.num_students, self, (x, y), "adult", self.schedule)
            self.schedule.append(adult)

    def step_continuous(self, dt):
        """Voer een continue tijdstap uit met delta tijd dt."""
        # Update de totale simulatietijd
        self.simulation_time += dt

        # Activeer alle agenten in willekeurige volgorde met delta tijd
        random.shuffle(self.schedule)
        for agent in self.schedule:
            agent.step_continuous(dt)

    def remove_agent(self, agent):
        """Verwijder een agent uit de simulatie."""
        if agent in self.schedule:
            self.schedule.remove(agent)
