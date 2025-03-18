from agents.schoolagent import SchoolAgent
import random


class AdultAgent(SchoolAgent):
    """Agent class for adults (teachers, staff) with basic behaviors."""

    def __init__(self, unique_id, model, position, agent_type, agents):
        # Fix parameter order to match SchoolAgent
        super().__init__(unique_id, model, agent_type, position, agents)
        self.response_delay = random.randint(2, 5)  # 2-5 time steps delay

    # Adult-specific behaviors can be added here as needed
    # For now we're just using the base SchoolAgent behavior