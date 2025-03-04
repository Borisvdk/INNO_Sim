import random
from agents.schoolagent import SchoolAgent


class AdultAgent(SchoolAgent):
    """Agent klasse voor volwassenen (docenten, personeel)."""

    def __init__(self, unique_id, model, position, ADULT):
        super().__init__(unique_id, model, ADULT, position)
        self.response_delay = random.randint(2, 5)  # 2-5 tijdstappen vertraging