from agents.schoolagent import SchoolAgent


class AdultAgent(SchoolAgent):
    """Simplified adult agent class that mostly inherits from SchoolAgent."""

    def __init__(self, unique_id, model, position, agent_type, agents):
        # SchoolAgent constructor already handles all adult-specific parameters
        super().__init__(unique_id, model, position, agent_type, agents)

        # Adult-specific behavior is initialized in the parent class
        # We only keep this class for backward compatibility and potential future expansion