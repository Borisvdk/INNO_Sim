from agents.schoolagent import SchoolAgent


class StudentAgent(SchoolAgent):
    """Agent klasse voor scholieren."""

    def __init__(self, unique_id, model, position, agent_type):
        super().__init__(unique_id, model, agent_type, position)
        self.fear_level = 0.0
        self.grab_weapon_prob = 0.05  # 5% kans om een wapen te pakken
        self.state = "Normal"  # "Normal", "Fleeing", "Hiding", "Attacking"