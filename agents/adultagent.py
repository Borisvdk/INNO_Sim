import random
from agents.schoolagent import SchoolAgent


class AdultAgent(SchoolAgent):
    """Agent class for adults (teachers, staff) with basic behaviors."""

    def __init__(self, unique_id, model, position, agent_type):
        # Initialize parent class
        super().__init__(unique_id, model, agent_type, position)

        # Adult-specific attributes
        self.response_delay = random.randint(2, 5)  # 2-5 time steps delay