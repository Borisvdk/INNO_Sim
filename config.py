# --- START OF FILE config.py ---

"""
Configuration file for the school safety simulation.
All important simulation parameters are defined here.
"""

# Basic simulation parameters
SIM_WIDTH = 600
SIM_HEIGHT = 400
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS_LIMIT = 60

# Agent counts
INITIAL_STUDENTS = 100
INITIAL_ADULTS = 20

# Weapon odds
ADULT_WEAPON_PROBABILITY = 0.5

# Agent physical properties
STUDENT_RADIUS = 3.0
ADULT_RADIUS = 4.0
STUDENT_MASS = 1.0
ADULT_MASS = 1.3
STUDENT_MAX_SPEED = 100.0
ADULT_MAX_SPEED = 80.0

# Idle behavior parameters
STUDENT_IDLE_PROBABILITY = 0.5
ADULT_IDLE_PROBABILITY = 0.7
STUDENT_IDLE_DURATION_RANGE = (1, 3)  # (min, max) in seconds
ADULT_IDLE_DURATION_RANGE = (1.5, 4)  # (min, max) in seconds
STUDENT_PATH_TIME_RANGE = (0.5, 2)  # (min, max) in seconds
ADULT_PATH_TIME_RANGE = (1, 3)  # (min, max) in seconds

# Movement & collision parameters
PERSONAL_SPACE_FACTOR = 3  # Multiple of agent radius
MIN_DISTANCE_FACTOR = 2    # Multiple of agent radius
AVOIDANCE_STRENGTH = 30.0
WALL_AVOIDANCE_STRENGTH = 50.0

# Shooter parameters
SHOOTER_CHECK_INTERVAL = 10.0  # Seconds between checks for random shooter emergence
SHOOTER_EMERGENCE_PROBABILITY = 0.01  # Probability per check (0.01 = 1%)
SHOOTING_INTERVAL = 2.0  # Seconds between shots
SHOOTING_RANGE = 25.0  # Units
HIT_PROBABILITY = 0.7  # Probability to hit target (0.5 = 50%)
SHOOTER_SEARCH_DURATION = 5.0  # How long shooter searches before changing strategy
STEAL_RANGE = 10.0  # Units within which a student can attempt to steal
STEAL_PROBABILITY = 0.001  # Probability per step to attempt stealing

# Response & awareness parameters
ADULT_RESPONSE_DELAY_RANGE = (2, 5)  # (min, max) time steps
# ***** NEW PARAMETER *****
AWARENESS_RANGE = 50  # Distance (units) within which students become aware of a shooter
# *************************

# Visualization parameters
VISION_CONE_ANGLE = 120  # Degrees
MAX_VISION_DISTANCE = 150  # Units # Still used for shooter visualization
SHOT_VISUALIZATION_DURATION = 0.5  # Seconds
ALERT_DURATION = 5.0  # Seconds

# Colors
COLORS = {
    "WHITE": (255, 255, 255),
    "BLUE": (0, 0, 255),  # Regular students
    "RED": (255, 0, 0),   # Adults
    "BLACK": (0, 0, 0),   # Walls and text
    "GREEN": (0, 255, 0),  # Shooter
    "ARMED_STUDENT": (100, 100, 255),
    "ARMED_ADULT": (255, 100, 100),
    "ALERT": (255, 0, 0)
}

# Key mappings (pygame key constants will be used in code)
KEY_MAPPING = {
    "SPEED_UP": "UP",
    "SPEED_DOWN": "DOWN",
    "RESET_SPEED": "SPACE",
    "ADD_STUDENTS": "s",
    "ADD_ADULTS": "a",
    "TOGGLE_LINE_OF_SIGHT": "v",
    "TOGGLE_SAFE_AREAS": "b",
    "EMERGENCY_EVACUATION": "e",
    "ADD_SHOOTER": "x"  # New key for manually adding a shooter
}
# --- END OF FILE config.py ---