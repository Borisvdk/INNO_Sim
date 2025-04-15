"""
Configuration file for the school safety simulation.
All important simulation parameters are defined here.
"""

# --- Simulation Environment ---
SIM_WIDTH = 600                     # Logical width of the simulation area
SIM_HEIGHT = 400                    # Logical height of the simulation area
GRID_FILE = "grid.json"             # File defining walls, doors, exits

# --- Display Settings ---
SCREEN_WIDTH = 1200                 # Width of the display window in pixels
SCREEN_HEIGHT = 800                 # Height of the display window in pixels
FPS_LIMIT = 60                      # Target frame rate for visualization
FPS_SAMPLE_COUNT = 30               # Number of frames to average for FPS display

# --- Simulation Control ---
NUM_VISUAL_BATCH_RUNS = 30          # Default number of simulations to run sequentially
INITIAL_SHOOTER_SPAWN_TIME = 5.0      # Seconds after start to spawn the first shooter (-1 to disable)
TERMINATION_DELAY_AFTER_SHOOTER = 60.0 # Seconds after first shooter appears to end sim
PAUSE_ON_TERMINATION = 1.5          # Seconds to pause visualization when simulation ends
PAUSE_BETWEEN_RUNS = 2.0            # Seconds to pause between sequential simulation runs

# --- Agent Initialization ---
INITIAL_STUDENTS = 208              # Starting number of students
INITIAL_ADULTS = 15                 # Starting number of adults

# --- Agent Spawning (Manual) ---
ADD_STUDENT_INCREMENT = 10          # Number of students to add with 'S' key
ADD_ADULT_INCREMENT = 5             # Number of adults to add with 'A' key

# --- Agent Physical Properties ---
STUDENT_RADIUS = 3.0                # Visual and collision radius for students
ADULT_RADIUS = 4.0                  # Visual and collision radius for adults
STUDENT_MASS = 1.0                  # Relative mass for physics/collisions
ADULT_MASS = 1.3                    # Relative mass for physics/collisions
STUDENT_MAX_SPEED = 100.0           # Maximum movement speed (units per second)
ADULT_MAX_SPEED = 80.0              # Maximum movement speed (units per second)

# --- Agent Behavior ---
STUDENT_IDLE_PROBABILITY = 0.5      # Chance per second a student might decide to idle
ADULT_IDLE_PROBABILITY = 0.7        # Chance per second an adult might decide to idle
STUDENT_IDLE_DURATION_RANGE = (1, 3) # (min, max) seconds for student idle state
ADULT_IDLE_DURATION_RANGE = (1.5, 4)# (min, max) seconds for adult idle state
STUDENT_PATH_TIME_RANGE = (0.5, 2)  # (min, max) seconds student follows a path before reconsidering
ADULT_PATH_TIME_RANGE = (1, 3)      # (min, max) seconds adult follows a path before reconsidering

# --- Movement & Collision ---
# These factors likely used within agent logic or SchoolModel collision handling
AVOIDANCE_STRENGTH = 30.0           # Factor for agent-agent avoidance force
WALL_AVOIDANCE_STRENGTH = 50.0      # Factor for agent-wall avoidance force
# PERSONAL_SPACE_FACTOR = 3         # (Uncomment if used) Multiplier for preferred distance
# MIN_DISTANCE_FACTOR = 2           # (Uncomment if used) Multiplier for minimum separation

# --- Shooter Behavior ---
# Random shooter emergence parameters (may be used in SchoolModel)
SHOOTER_CHECK_INTERVAL = 10.0       # Seconds between checks for random shooter emergence
SHOOTER_EMERGENCE_PROBABILITY = 0.01# Probability per check that an agent becomes a shooter

ARMED_ADULTS_COUNT = 0             # Amount of adults starting with / acquires a weapon
SHOOTING_INTERVAL = 2.0             # Seconds between shots for a shooter
SHOOTING_RANGE = 100.0              # Max distance a shooter can fire (units)
HIT_PROBABILITY = 0.7               # Base probability to hit target within range
SHOOTER_SEARCH_DURATION = 5.0       # How long shooter searches before changing strategy (used in shooter agent logic)
STEAL_RANGE = 10.0                  # Max distance for a student to attempt stealing a weapon (used in student agent logic)
STEAL_PROBABILITY = 0.001           # Probability per step for a student to attempt stealing (used in student agent logic)

# --- Response & Awareness ---
ADULT_RESPONSE_DELAY_RANGE = (0.5, 2.0) # (min, max) seconds delay before adult reacts to threat (used in adult agent logic)
AWARENESS_RANGE = 200                # Distance to passively become aware of shooter/threat (used in agent logic)
SCREAM_RADIUS = 30                  # Distance a student's scream travels, potentially alerting others
ENABLE_STUDENT_SCREAMING = True     # Whether students scream when in emergency (affects awareness spread)

# --- Visualization ---
VISION_CONE_ANGLE = 120             # Field of view angle for shooter visualization (degrees)
MAX_VISION_DISTANCE = 150           # Max distance for shooter vision cone visualization (units)
SHOT_VISUALIZATION_DURATION = 0.25  # Seconds a shot line remains visible
ALERT_DURATION = 5.0                # Seconds the "ACTIVE SHOOTER" alert is shown

# --- Sound ---
GUNSHOT_SOUND_FILE = "gunshot.wav"  # Path to gunshot sound effect
KILL_SOUND_FILE = "kill.wav"        # Path to sound effect when agent is hit/killed
SOUND_VOLUME = 0.4                  # Default volume for sound effects (0.0 to 1.0)

# --- Colors ---
COLORS = {
    # Basic Environment
    "WHITE": (255, 255, 255),
    "BLACK": (0, 0, 0),             # Walls, some text
    "BROWN": (139, 69, 19),         # Doors

    # Agents
    "BLUE": (0, 0, 255),            # Regular students
    "FLEEING_STUDENT": (0, 100, 255),# Students in emergency
    "RED": (200, 0, 0),             # Regular adults (less intense red)
    "AWARE_ADULT": (255, 100, 0),   # Adults aware of shooter
    "GREEN": (0, 255, 0),           # Shooter agent
    "ARMED_STUDENT": (100, 100, 255),# Student who somehow got a weapon (if implemented)
    "ARMED_ADULT": (255, 255, 0),   # Adults with weapons (Yellow)

    # UI & Effects
    "PANEL_BG": (50, 50, 50, 180),  # Semi-transparent dark gray for UI panels
    "TEXT_COLOR": (240, 240, 240),  # Light text color for UI panels
    "ALERT": (255, 0, 0),           # Color for shooter count text when > 0, shots
    "SHOT": (255, 0, 0),            # Color of the shot visualization line
    "SCREAM_FILL": (255, 165, 0, 40),# Fainter orange fill for scream radius
    "SCREAM_OUTLINE": (255, 165, 0, 80),# Fainter orange outline for scream radius
    "EXIT_FILL": (0, 200, 0, 80),   # Semi-transparent green for exit areas
    "EXIT_BORDER": (0, 100, 0, 150) # Darker green border for exit areas
}
