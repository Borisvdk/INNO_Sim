import random
from agents.schoolagent import SchoolAgent


class AdultAgent(SchoolAgent):
    """Agent klasse voor volwassenen (docenten, personeel)."""

    def __init__(self, unique_id, model, position, agent_type, agents):
        super().__init__(unique_id, model, agent_type, position, agents)
        self.response_delay = random.randint(2, 5)  # 2-5 tijdstappen vertraging