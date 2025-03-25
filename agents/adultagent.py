from agents.schoolagent import SchoolAgent
import random

class AdultAgent(SchoolAgent):
    """Agent class for adults (teachers, staff) with basic behaviors."""
    def __init__(self, unique_id, model, position, agent_type):
        # Roep de ouderklasse aan
        super().__init__(unique_id, model, agent_type, position)
        # Adult-specifieke attributen
        self.response_delay = random.randint(2, 5)  # 2-5 tijdstappen delay
        # Stel een standaardkleur in (bijvoorbeeld rood)
        self.color = (255, 0, 0)  # Rood als standaardkleur