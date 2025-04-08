import math
import random
import os
from grid_converter import integrate_grid_into_simulation
import config
import pygame # Ensure pygame is imported
from a_star import astar
import time


class AgentFactory:
    """Factory class for creating different types of agents."""

    @staticmethod
    def create_agent(agent_type, unique_id, model, position, is_shooter=False):
        """Create and return an agent of the specified type."""
        if agent_type == "student":
            from agents.studentagent import StudentAgent
            agent = StudentAgent(unique_id, model, position, agent_type)
            if is_shooter:
                agent.is_shooter = True
                agent.has_weapon = True
            return agent
        elif agent_type == "adult":
            from agents.adultagent import AdultAgent
            return AdultAgent(unique_id, model, position, agent_type)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")


class SpatialGrid:
    """An optimized grid-based spatial partitioning system for efficiently finding nearby agents."""

    def __init__(self, width, height, cell_size):
        self.cell_size = cell_size
        self.grid_width = math.ceil(width / cell_size)
        self.grid_height = math.ceil(height / cell_size)
        self.grid = {}  # Dictionary of {(cell_x, cell_y): [agents]}
        self.agent_positions = {}  # Track each agent's last position and cell: {agent: ((x,y), (cell_x, cell_y))}

    def clear(self):
        """Clear all cells in the grid."""
        self.grid = {}
        self.agent_positions = {}

    def _get_cell_indices(self, position):
        """Convert a position to grid cell indices."""
        x, y = position
        cell_x = int(x / self.cell_size)
        cell_y = int(y / self.cell_size)
        return cell_x, cell_y

    def update_agent(self, agent):
        """Update an agent's position in the grid, only if needed."""
        current_position = agent.position
        current_cell = self._get_cell_indices(current_position)

        # Check if we've seen this agent before and if it moved cells
        if agent in self.agent_positions:
            last_position, last_cell = self.agent_positions[agent]

            # If cell hasn't changed, do nothing
            if last_cell == current_cell:
                self.agent_positions[agent] = (current_position, current_cell)
                return

            # Remove from old cell
            if last_cell in self.grid and agent in self.grid[last_cell]:
                self.grid[last_cell].remove(agent)
                if not self.grid[last_cell]:  # Clean up empty cells
                    del self.grid[last_cell]

        # Add to new cell
        if current_cell not in self.grid:
            self.grid[current_cell] = []
        self.grid[current_cell].append(agent)

        # Update tracked position
        self.agent_positions[agent] = (current_position, current_cell)

    def remove_agent(self, agent):
        """Remove an agent from the grid."""
        if agent in self.agent_positions:
            _, cell = self.agent_positions[agent]
            if cell in self.grid and agent in self.grid[cell]:
                self.grid[cell].remove(agent)
                if not self.grid[cell]:  # Clean up empty cells
                    del self.grid[cell]
            del self.agent_positions[agent]

    def get_nearby_agents(self, position, radius):
        """Get all agents within a certain radius of a position."""
        center_x, center_y = position
        cell_radius = math.ceil(radius / self.cell_size)
        cell_x, cell_y = self._get_cell_indices(position)

        nearby_agents = []

        # Check all cells in the region
        for dx in range(-cell_radius, cell_radius + 1):
            for dy in range(-cell_radius, cell_radius + 1):
                cell_key = (cell_x + dx, cell_y + dy)
                if cell_key in self.grid:
                    nearby_agents.extend(self.grid[cell_key])

        return nearby_agents


class SchoolModel:
    def __init__(self, n_students=config.INITIAL_STUDENTS, n_adults=config.INITIAL_ADULTS,
                 width=config.SIM_WIDTH, height=config.SIM_HEIGHT,
                 adult_weapon_percentage=config.ADULT_WEAPON_PROBABILITY,
                 grid_file=None):
        """
        Initialize the school simulation model.
        """
        self.num_students = n_students
        self.num_adults = n_adults
        self.width = width
        self.height = height
        self.adult_weapon_percentage = adult_weapon_percentage
        self.running = True
        self.schedule = []
        self.active_shots = []
        self.simulation_time = 0.0
        self.active_shooters = set()
        self.shooter_check_interval = config.SHOOTER_CHECK_INTERVAL
        self.last_shooter_check_time = 0.0
        self.shooter_emergence_probability = config.SHOOTER_EMERGENCE_PROBABILITY
        self.spatial_grid = SpatialGrid(width, height, cell_size=max(config.STUDENT_RADIUS, config.ADULT_RADIUS) * 4)

        self.shooter_appeared_flag = False
        self.first_shooter_appearance_time = 0.0
        self.terminate_simulation = False

        # --- Data Collection Attributes ---
        self.initial_student_count = n_students
        self.initial_adult_count = n_adults
        self.dead_student_count = 0
        self.dead_adult_count = 0
        self.escaped_student_count = 0
        # ----------------------------------

        # --- Wall and Exit Loading ---
        self.walls = []  # Now list of pygame.Rect
        self.exits = []  # List of pygame.Rect for exits
        self.doors = []

        if grid_file and os.path.exists(grid_file):
                print(f"Loading elements from grid file: {grid_file}")
                # integrate_grid_into_simulation now returns (walls, exits, doors)
                loaded_walls, loaded_exits, loaded_doors = integrate_grid_into_simulation(grid_file, width, height)
                self.walls = loaded_walls
                self.exits = loaded_exits
                self.doors = loaded_doors # <-- Store loaded doors
                print(f"Model initialized with {len(self.walls)} walls, {len(self.exits)} exits, {len(self.doors)} doors.")
                if not self.exits and not self.doors and not self.walls:
                    print("Warning: Grid file loaded but resulted in zero walls, exits, or doors.")
                elif not self.exits:
                    print("Warning: No exits defined in the grid file!")
        else:
            print("Warning: Grid file not found or not specified. Using default empty walls/exits/doors.")

            wall_thickness = 5 # Example thickness
            self.walls.append(pygame.Rect(0, 0, width, wall_thickness)) # Top
            self.walls.append(pygame.Rect(0, height - wall_thickness, width, wall_thickness)) # Bottom
            self.walls.append(pygame.Rect(0, 0, wall_thickness, height)) # Left
            self.walls.append(pygame.Rect(width - wall_thickness, 0, wall_thickness, height)) # Right
            # Define a default exit if desired when no grid file is used
            # self.exits.append(pygame.Rect(width * 0.8, 0, width * 0.1, 10)) # Example top-right exit

        self.wall_rects = self.walls # This list is used for pathfinding obstacles

        # --- Combine walls and doors for vision checks ---
        # This can be done here or dynamically in the utility functions
        self.visual_obstacles = self.walls + self.doors # <-- Pre-combine for LoS/Raycasting

        self._create_all_agents()


    # In the _create_all_agents method of SchoolModel, ensure adults with weapons are properly configured:

    def _create_all_agents(self):
        """Create all agents at safe positions - no shooter at the beginning"""
        # Generate safe positions for all agents ahead of time
        all_positions = []
        min_distance_between_agents = 8.0  # Ensure agents aren't too close to each other

        for _ in range(self.num_students + self.num_adults):
            # Generate a new position that's not too close to existing agents or walls
            for attempt in range(100):  # Limit attempts to prevent infinite loops
                position = self.generate_safe_position(min_wall_distance=5.0)

                # Check if too close to other agents
                too_close = False
                for existing_pos in all_positions:
                    dx = position[0] - existing_pos[0]
                    dy = position[1] - existing_pos[1]
                    if dx * dx + dy * dy < min_distance_between_agents ** 2:
                        too_close = True
                        break

                if not too_close:
                    all_positions.append(position)
                    break

            # Fallback if we couldn't find a good position
            if attempt == 99 and too_close:
                print("Warning: Could not find position far enough from other agents")
                all_positions.append(position)  # Use the last attempt

        # Create student agents with safe positions - no shooter initially
        for i in range(self.num_students):
            position = all_positions[i]
            agent = AgentFactory.create_agent("student", i, self, position, is_shooter=False)
            self.schedule.append(agent)
            self.spatial_grid.update_agent(agent)

        # Create adult agents with safe positions
        for i in range(self.num_adults):
            position = all_positions[i + self.num_students]
            agent = AgentFactory.create_agent("adult", i + self.num_students, self, position)

            # Configure if this adult has a weapon
            if random.random() < self.adult_weapon_percentage:
                agent.has_weapon = True
                agent.color = (255, 255, 0)  # Yellow for armed adults
                print(f"Adult {agent.unique_id} is armed and ready to respond")
            else:
                agent.has_weapon = False

            self.schedule.append(agent)
            self.spatial_grid.update_agent(agent)

    def step_continuous(self, dt):
        """Perform a continuous time step with delta time dt."""
        if self.terminate_simulation:
             # Optioneel: print hier nog iets of doe niks extra's.
             # De main loop zal de property `should_terminate` checken.
             return # Stop verdere verwerking van deze stap

        self.simulation_time += dt

        # Check for random shooter emergence
        if not self.has_active_shooter and self.simulation_time - self.last_shooter_check_time >= self.shooter_check_interval:
            self.last_shooter_check_time = self.simulation_time
            self._check_for_shooter_emergence() # Deze functie zet mogelijk has_active_shooter op True

        # Check if a shooter has appeared
        if self.has_active_shooter and not self.shooter_appeared_flag:
            self.shooter_appeared_flag = True
            self.first_shooter_appearance_time = self.simulation_time
            print(f"--- EERSTE SCHUTTER GEDETECTEERD op tijd {self.simulation_time:.1f}s. Simulatie eindigt over {config.TERMINATION_DELAY_AFTER_SHOOTER}s ---")

        # Check if the simulation should terminate after a shooter appears
        if self.shooter_appeared_flag:
            if self.simulation_time - self.first_shooter_appearance_time >= config.TERMINATION_DELAY_AFTER_SHOOTER:
                self.terminate_simulation = True
                print(f"--- SIMULATIE TERMINATIE GETRIGGERD op tijd {self.simulation_time:.1f}s ---")
                # We stoppen niet direct hier, maar zetten de flag zodat de main loop kan stoppen.

        # Shuffle and step agents
        random.shuffle(self.schedule) # Consider if shuffling is still needed or detrimental
        agents_to_process = list(self.schedule) # Create copy in case agents are removed during step
        for agent in agents_to_process:
            # Ensure agent is still in the main schedule before stepping
            if agent in self.schedule:
                 agent.step_continuous(dt) # Stap van de agent uitvoeren


    def _check_for_shooter_emergence(self):
        """Check if a random student spontaneously becomes a shooter."""
        if random.random() > self.shooter_emergence_probability:
            return
        student_agents = [
            agent for agent in self.schedule
            if agent.agent_type == "student" and not agent.is_shooter
        ]
        if not student_agents:
            return
        random_student = random.choice(student_agents)
        random_student.is_shooter = True
        random_student.has_weapon = True
        self.active_shooters.add(random_student)
        print(f"ALERT: Student {random_student.unique_id} has become an active shooter "
              f"at time {self.simulation_time:.1f}s")

    def add_manual_shooter(self):
        """Manually convert a random student into a shooter."""
        student_agents = [
            agent for agent in self.schedule
            if agent.agent_type == "student" and not agent.is_shooter
        ]
        if not student_agents:
            print("No eligible students available to become a shooter.")
            return False
        random_student = random.choice(student_agents)
        random_student.is_shooter = True
        random_student.has_weapon = True
        self.active_shooters.add(random_student)
        print(f"MANUAL ALERT: Student {random_student.unique_id} has become an active shooter "
              f"at time {self.simulation_time:.1f}s")
        
        if not self.shooter_appeared_flag:
            self.shooter_appeared_flag = True
            self.first_shooter_appearance_time = self.simulation_time
            print(f"--- EERSTE SCHUTTER (handmatig) GEDETECTEERD op tijd {self.simulation_time:.1f}s. Simulatie eindigt over {config.TERMINATION_DELAY_AFTER_SHOOTER}s ---")

        return True

    @property
    def has_active_shooter(self):
        """Check if there is at least one active shooter."""
        return len(self.active_shooters) > 0
    
    @property
    def should_terminate(self):
        """Property om aan te geven of de simulatie moet stoppen."""
        return self.terminate_simulation
    
    @property
    def exit_rects(self):
        return self.exits
    
    @property
    def vision_blocking_obstacles(self):
        """Returns a combined list of walls and doors for vision checks."""
        return self.walls + self.doors

    def add_students(self, count):
        """Add a specified number of students to the simulation."""
        for _ in range(count):
            position = self.generate_safe_position(min_wall_distance=5.0)
            agent = AgentFactory.create_agent("student", len(self.schedule), self, position)
            self.schedule.append(agent)
            self.spatial_grid.update_agent(agent)

    def add_adults(self, count):
        """Add a specified number of adults to the simulation."""
        for _ in range(count):
            position = self.generate_safe_position(min_wall_distance=5.0)
            agent = AgentFactory.create_agent("adult", len(self.schedule), self, position)
            self.schedule.append(agent)
            self.spatial_grid.update_agent(agent)

    # Ensure generate_safe_position is updated if necessary
    def generate_safe_position(self, min_wall_distance=5.0, max_attempts=100):
         """
         Generate a random position that's not too close to a wall Rect.
         """
         padding = max(5.0, min_wall_distance)

         for _ in range(max_attempts):
             x = random.uniform(padding, self.width - padding)
             y = random.uniform(padding, self.height - padding)

             if self.is_position_safe((x, y), min_wall_distance):
                 return (x, y)

         print("Warning: Could not find ideal safe position after", max_attempts, "attempts")
         return self.find_safest_position(padding) # Fallback

      # --- Modify generate_safe_position and is_position_safe to use pygame.Rect ---
    def is_position_safe(self, position, min_wall_distance=5.0):
        """
        Check if a position is at a safe distance from all wall Rects.
        """
        x, y = position
        agent_radius = min_wall_distance # Use min_wall_distance as effective radius check

        for wall_rect in self.walls:
            # Check collision using inflate to account for distance
            # Inflate creates a larger rect; if point is inside inflated rect, it's too close
            inflated_wall = wall_rect.inflate(agent_radius * 2, agent_radius * 2)
            if inflated_wall.collidepoint(x, y):
                 return False # Too close to this wall

            # Also check if point is exactly inside the original wall
            if wall_rect.collidepoint(x,y):
                 return False # Inside the wall exactly

        return True

    # In find_safest_position, update the wall check:
    def find_safest_position(self, padding):
        """
        Find the position with maximum distance to any wall Rect.
        """
        grid_size = 20
        candidates = []

        for i in range(grid_size):
            for j in range(grid_size):
                x = padding + (self.width - 2 * padding) * i / (grid_size - 1)
                y = padding + (self.height - 2 * padding) * j / (grid_size - 1)

                min_distance = float('inf')
                inside_wall = False

                for wall_rect in self.walls:
                    if wall_rect.collidepoint(x, y):
                        inside_wall = True
                        break # Skip if inside wall

                    # Calculate distance to closest point on Rect boundary
                    clamped_x = max(wall_rect.left, min(x, wall_rect.right))
                    clamped_y = max(wall_rect.top, min(y, wall_rect.bottom))
                    dx = x - clamped_x
                    dy = y - clamped_y
                    distance = math.hypot(dx, dy)
                    min_distance = min(min_distance, distance)

                if inside_wall:
                    continue

                candidates.append((x, y, min_distance))

        if candidates:
            candidates.sort(key=lambda c: -c[2])
            return (candidates[0][0], candidates[0][1])
        else:
            print("Warning: No safe position found, using center.")
            return (self.width / 2, self.height / 2)

    def remove_agent(self, agent, reason="died"):
        """
        Remove an agent from the simulation and update counts based on reason.
        Reason can be 'died' or 'escaped'.
        """
        if agent in self.schedule:
            # Update counts based on reason *before* removing
            if reason == "died":
                if agent.agent_type == "student":
                    self.dead_student_count += 1
                elif agent.agent_type == "adult":
                    self.dead_adult_count += 1
            elif reason == "escaped":
                 # Only count students escaping for now
                if agent.agent_type == "student":
                     self.escaped_student_count += 1

            # Remove from active shooters set if necessary
            if agent in self.active_shooters:
                self.active_shooters.remove(agent)
                print(f"Shooter {agent.unique_id} removed ({reason}). Active shooters left: {len(self.active_shooters)}")

            # Remove from spatial grid and schedule
            self.spatial_grid.remove_agent(agent)
            self.schedule.remove(agent) # Remove from the main list


    def collect_step_data(self):
        """Collects statistics for the current simulation step."""
        # --- Optional Throttling ---
        # current_time = self.simulation_time
        # if current_time - self.last_data_collect_time < self.data_collect_interval:
        #     return None # Don't collect data yet
        # self.last_data_collect_time = current_time
        # ---------------------------

        living_students = 0
        living_adults = 0
        living_armed_adults = 0
        living_unarmed_adults = 0
        living_shooters = 0 # Count shooters currently in schedule

        for agent in self.schedule:
            if agent.agent_type == "student":
                living_students += 1
                if getattr(agent, 'is_shooter', False):
                    living_shooters += 1
            elif agent.agent_type == "adult":
                living_adults += 1
                if getattr(agent, 'has_weapon', False):
                    living_armed_adults += 1
                else:
                    living_unarmed_adults += 1
                # Optional: Count adult shooters if adults can become shooters
                # if getattr(agent, 'is_shooter', False):
                #    living_shooters += 1 # Add if needed

        # Sanity check: ensure living shooters count matches active_shooters set
        # It might differ slightly if an agent is removed mid-step *after* counting
        # Using len(self.active_shooters) is likely more accurate for *current* state.
        living_shooters = len(self.active_shooters)

        # Total deaths are tracked directly
        total_dead_students = self.dead_student_count
        total_dead_adults = self.dead_adult_count

        # Total escaped students are tracked directly
        total_escaped_students = self.escaped_student_count

        data = {
            "Time": round(self.simulation_time, 2), # Round time for cleaner output
            "Living Students": living_students,
            "Living Adults": living_adults,
            "Living Armed Adults": living_armed_adults,
            "Living Unarmed Adults": living_unarmed_adults,
            "Living Shooters": living_shooters,
            "Dead Students": total_dead_students,
            "Dead Adults": total_dead_adults,
            "Escaped Students": total_escaped_students
        }
        return data
