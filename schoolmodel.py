import math
import random
import os
from grid_converter import integrate_grid_into_simulation
import config
import pygame


class AgentFactory:
    """Factory class for creating different types of agents."""

    @staticmethod
    def create_agent(agent_type, unique_id, model, position, is_shooter=False):
        """
        Create and return an agent instance based on the specified type.

        Args:
            agent_type (str): The type of agent to create ("student" or "adult").
            unique_id: A unique identifier for the new agent.
            model: The simulation model instance.
            position (tuple): The initial (x, y) position for the agent.
            is_shooter (bool, optional): If True and agent_type is "student", creates a shooter student.
                                         Defaults to False.

        Returns:
            SchoolAgent: An instance of the requested agent subclass.

        Raises:
            ValueError: If an unknown agent_type is provided.
        """
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
        """
        Initialize the SpatialGrid.

        Args:
            width (int): The width of the simulation area.
            height (int): The height of the simulation area.
            cell_size (int): The size of each grid cell. Should be larger than the largest agent radius.
        """
        self.cell_size = cell_size
        self.grid_width = math.ceil(width / cell_size)
        self.grid_height = math.ceil(height / cell_size)
        self.grid = {}
        self.agent_positions = {}

    def clear(self):
        """Clear all agents and cells from the grid."""
        self.grid = {}
        self.agent_positions = {}

    def _get_cell_indices(self, position):
        """
        Convert world coordinates to grid cell indices.

        Args:
            position (tuple): The (x, y) world coordinates.

        Returns:
            tuple: The (cell_x, cell_y) grid indices.
        """
        x, y = position
        cell_x = int(x / self.cell_size)
        cell_y = int(y / self.cell_size)
        return cell_x, cell_y

    def update_agent(self, agent):
        """
        Update an agent's position within the spatial grid. If the agent moved to a new cell,
        it is removed from the old cell's list and added to the new one.

        Args:
            agent (SchoolAgent): The agent instance to update.
        """
        current_position = agent.position
        current_cell = self._get_cell_indices(current_position)

        if agent in self.agent_positions:
            last_position, last_cell = self.agent_positions[agent]

            if last_cell == current_cell:
                self.agent_positions[agent] = (current_position, current_cell)
                return

            if last_cell in self.grid and agent in self.grid[last_cell]:
                self.grid[last_cell].remove(agent)
                if not self.grid[last_cell]:
                    del self.grid[last_cell]

        if current_cell not in self.grid:
            self.grid[current_cell] = []
        self.grid[current_cell].append(agent)

        self.agent_positions[agent] = (current_position, current_cell)

    def remove_agent(self, agent):
        """
        Remove an agent completely from the spatial grid.

        Args:
            agent (SchoolAgent): The agent instance to remove.
        """
        if agent in self.agent_positions:
            _, cell = self.agent_positions[agent]
            if cell in self.grid and agent in self.grid[cell]:
                self.grid[cell].remove(agent)
                if not self.grid[cell]:
                    del self.grid[cell]
            del self.agent_positions[agent]

    def get_nearby_agents(self, position, radius):
        """
        Retrieve a list of all agents located in cells that overlap with the specified radius around a position.
        Note: This returns agents in nearby cells; further distance checking might be needed.

        Args:
            position (tuple): The center (x, y) coordinates of the search area.
            radius (float): The search radius.

        Returns:
            list: A list of agent instances potentially within the radius.
        """
        center_x, center_y = position
        cell_radius = math.ceil(radius / self.cell_size)
        cell_x, cell_y = self._get_cell_indices(position)

        nearby_agents = []

        for dx in range(-cell_radius, cell_radius + 1):
            for dy in range(-cell_radius, cell_radius + 1):
                cell_key = (cell_x + dx, cell_y + dy)
                if cell_key in self.grid:
                    nearby_agents.extend(self.grid[cell_key])

        return nearby_agents


class SchoolModel:
    """
    The main simulation model managing agents, environment, and simulation state.
    """
    def __init__(self, n_students=config.INITIAL_STUDENTS, n_adults=config.INITIAL_ADULTS,
                 width=config.SIM_WIDTH, height=config.SIM_HEIGHT,
                 armed_adults_count=config.ARMED_ADULTS_COUNT,
                 grid_file=None):
        """
        Initialize the school simulation model.

        Args:
            n_students (int): Initial number of student agents.
            n_adults (int): Initial number of adult agents.
            width (int): Width of the simulation area.
            height (int): Height of the simulation area.
            armed_adults_count (int): The number of adults who should start with weapons.
            grid_file (str, optional): Path to the JSON grid file defining walls, exits, doors. Defaults to None.
        """
        self.num_students = n_students
        self.num_adults = n_adults
        self.width = width
        self.height = height
        self.armed_adults_count = armed_adults_count
        self.armed_adults_current = 0
        self.running = True
        self.schedule = []
        self.active_shots = []
        self.simulation_time = 0.0
        self.active_shooters = set()
        self.shooter_check_interval = config.SHOOTER_CHECK_INTERVAL
        self.last_shooter_check_time = 0.0
        self.shooter_emergence_probability = config.SHOOTER_EMERGENCE_PROBABILITY
        self.spatial_grid = SpatialGrid(width, height, cell_size=max(config.STUDENT_RADIUS, config.ADULT_RADIUS) * 4)

        self.initial_shooter_spawn_time = config.INITIAL_SHOOTER_SPAWN_TIME
        self.initial_shooter_spawned = False
        self.shooter_appeared_flag = False
        self.first_shooter_appearance_time = 0.0
        self.terminate_simulation = False
        self.termination_reason = None

        self.initial_student_count = n_students
        self.initial_adult_count = n_adults
        self.dead_student_count = 0
        self.dead_adult_count = 0
        self.escaped_student_count = 0

        self.walls = []
        self.exits = []
        self.doors = []

        if grid_file and os.path.exists(grid_file):
            print(f"Loading elements from grid file: {grid_file}")
            loaded_walls, loaded_exits, loaded_doors = integrate_grid_into_simulation(grid_file, width, height)
            self.walls = loaded_walls
            self.exits = loaded_exits
            self.doors = loaded_doors
            print(f"Model initialized with {len(self.walls)} walls, {len(self.exits)} exits, {len(self.doors)} doors.")
            if not self.exits and not self.doors and not self.walls:
                print("Warning: Grid file loaded but resulted in zero walls, exits, or doors.")
            elif not self.exits:
                print("Warning: No exits defined in the grid file!")
        else:
            print("Warning: Grid file not found or not specified. Using default empty walls/exits/doors.")

            wall_thickness = 5
            self.walls.append(pygame.Rect(0, 0, width, wall_thickness))
            self.walls.append(pygame.Rect(0, height - wall_thickness, width, wall_thickness))
            self.walls.append(pygame.Rect(0, 0, wall_thickness, height))
            self.walls.append(pygame.Rect(width - wall_thickness, 0, wall_thickness, height))


        self.wall_rects = self.walls

        self.visual_obstacles = self.walls + self.doors

        self._create_all_agents()

    def _create_all_agents(self):
        """Create and place all initial student and adult agents in safe positions."""
        all_positions = []
        min_distance_between_agents = 8.0

        for _ in range(self.num_students + self.num_adults):
            for attempt in range(100):
                position = self.generate_safe_position(min_wall_distance=5.0)

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

            if attempt == 99 and too_close:
                print("Warning: Could not find position far enough from other agents")
                all_positions.append(position)

        for i in range(self.num_students):
            position = all_positions[i]
            agent = AgentFactory.create_agent("student", i, self, position, is_shooter=False)
            self.schedule.append(agent)
            self.spatial_grid.update_agent(agent)

        armed_adults_to_create = min(self.armed_adults_count, self.num_adults)
        armed_indices = random.sample(range(self.num_adults), armed_adults_to_create)

        for i in range(self.num_adults):
            position = all_positions[i + self.num_students]
            agent = AgentFactory.create_agent("adult", i + self.num_students, self, position)

            if i in armed_indices:
                agent.has_weapon = True
                agent.color = (255, 255, 0)
                self.armed_adults_current += 1
                print(f"Adult {agent.unique_id} is armed and ready to respond")
            else:
                agent.has_weapon = False

            self.schedule.append(agent)
            self.spatial_grid.update_agent(agent)

    def step_continuous(self, dt):
        """
        Advance the simulation by one continuous time step.

        Args:
            dt (float): The duration of the time step.
        """
        if self.terminate_simulation:
            return

        self.simulation_time += dt

        if not self.has_active_shooter and self.simulation_time - self.last_shooter_check_time >= self.shooter_check_interval:
            self.last_shooter_check_time = self.simulation_time
            self._check_for_shooter_emergence()

        if not self.initial_shooter_spawned and \
                0 <= self.initial_shooter_spawn_time <= self.simulation_time:
            print(f"--- Time reached ({self.simulation_time:.2f}s). Attempting to spawn initial timed shooter... ---")
            success = self.add_manual_shooter()
            if success:
                print(f"--- Initial timed shooter successfully spawned at time {self.simulation_time:.2f}s. ---")
            else:
                print(
                    f"--- WARNING: Failed to spawn initial timed shooter at {self.simulation_time:.2f}s (no eligible students?). ---")
            self.initial_shooter_spawned = True

        if (self.initial_shooter_spawn_time < 0 or self.initial_shooter_spawned) and \
                not self.has_active_shooter and \
                self.simulation_time - self.last_shooter_check_time >= self.shooter_check_interval:
            self.last_shooter_check_time = self.simulation_time
            if config.SHOOTER_EMERGENCE_PROBABILITY > 0:
                self._check_for_shooter_emergence()

        if self.has_active_shooter and not self.shooter_appeared_flag:
            self.shooter_appeared_flag = True
            self.first_shooter_appearance_time = self.simulation_time
            print(
                f"--- FIRST SHOOTER DETECTED at time {self.simulation_time:.1f}s. Simulation ends in {config.TERMINATION_DELAY_AFTER_SHOOTER}s ---")

        if self.shooter_appeared_flag:
            if self.simulation_time - self.first_shooter_appearance_time >= config.TERMINATION_DELAY_AFTER_SHOOTER:
                if not self.terminate_simulation:
                    self.terminate_simulation = True
                    self.termination_reason = f"Timeout after shooter ({config.TERMINATION_DELAY_AFTER_SHOOTER}s)"
                    print(
                        f"--- SIMULATION TERMINATION TRIGGERED at time {self.simulation_time:.1f}s ({self.termination_reason}) ---")


        random.shuffle(self.schedule)
        agents_to_process = list(self.schedule)
        for agent in agents_to_process:
            if agent in self.schedule:
                agent.step_continuous(dt)

    def _check_for_shooter_emergence(self):
        """Randomly checks if an eligible student becomes a shooter based on configured probability."""
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
        """
        Manually designates a random non-shooter student as a shooter.

        Returns:
            bool: True if a shooter was successfully added, False otherwise (e.g., no eligible students).
        """
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
            print(
                f"--- FIRST SHOOTER (manual) DETECTED at time {self.simulation_time:.1f}s. Simulation ends in {config.TERMINATION_DELAY_AFTER_SHOOTER}s ---")

        return True

    @property
    def has_active_shooter(self):
        """
        bool: True if there is at least one agent currently designated as a shooter, False otherwise.
        """
        return len(self.active_shooters) > 0

    @property
    def should_terminate(self):
        """
        bool: Indicates whether the simulation termination condition has been met.
        """
        return self.terminate_simulation

    @property
    def exit_rects(self):
        """
        list: A list of pygame.Rect objects representing the exit areas in the simulation.
        """
        return self.exits

    @property
    def vision_blocking_obstacles(self):
        """
        list: A combined list of pygame.Rect objects for walls and doors, used for line-of-sight checks.
        """
        return self.walls + self.doors

    def add_students(self, count):
        """
        Adds a specified number of new student agents to the simulation at safe locations.

        Args:
            count (int): The number of students to add.
        """
        current_id = len(self.schedule) + self.dead_student_count + self.escaped_student_count + self.dead_adult_count
        for i in range(count):
            position = self.generate_safe_position(min_wall_distance=5.0)
            agent = AgentFactory.create_agent("student", current_id + i, self, position)
            self.schedule.append(agent)
            self.spatial_grid.update_agent(agent)
        self.num_students += count

    def add_adults(self, count):
        """
        Adds a specified number of new adult agents, potentially arming some based on configuration.

        Args:
            count (int): The number of adults to add.
        """
        current_id = len(self.schedule) + self.dead_student_count + self.escaped_student_count + self.dead_adult_count

        remaining_armed_slots = max(0, self.armed_adults_count - self.armed_adults_current)
        armed_to_add = min(count, remaining_armed_slots)

        armed_indices = random.sample(range(count), armed_to_add) if armed_to_add > 0 else []

        for i in range(count):
            position = self.generate_safe_position(min_wall_distance=5.0)
            agent = AgentFactory.create_agent("adult", current_id + i, self, position)

            if i in armed_indices:
                agent.has_weapon = True
                self.armed_adults_current += 1
                print(f"Added Adult {agent.unique_id} is armed.")
            else:
                agent.has_weapon = False

            self.schedule.append(agent)
            self.spatial_grid.update_agent(agent)
        self.num_adults += count

    def generate_safe_position(self, min_wall_distance=5.0, max_attempts=100):
        """
        Generates a random (x, y) position within the simulation bounds that is not too close to any wall or door.

        Args:
            min_wall_distance (float, optional): The minimum required distance from any wall or door edge. Defaults to 5.0.
            max_attempts (int, optional): The maximum number of attempts to find a suitable position. Defaults to 100.

        Returns:
            tuple: An (x, y) tuple representing a safe position, or a fallback position if no ideal spot is found.
        """
        padding = max(5.0, min_wall_distance)

        for _ in range(max_attempts):
            x = random.uniform(padding, self.width - padding)
            y = random.uniform(padding, self.height - padding)

            if self.is_position_safe((x, y), min_wall_distance):
                return (x, y)

        print("Warning: Could not find ideal safe position after", max_attempts, "attempts")
        return self.find_safest_position(padding)

    def is_position_safe(self, position, min_wall_distance=5.0):
        """
        Checks if a given position is sufficiently far from all walls and doors.

        Args:
            position (tuple): The (x, y) position to check.
            min_wall_distance (float, optional): The minimum allowed distance to an obstacle. Defaults to 5.0.

        Returns:
            bool: True if the position is safe, False otherwise.
        """
        x, y = position
        agent_radius = min_wall_distance

        if not (agent_radius <= x <= self.width - agent_radius and
                agent_radius <= y <= self.height - agent_radius):
            return False

        for wall_rect in self.walls:
            inflated_wall = wall_rect.inflate(agent_radius * 2, agent_radius * 2)
            if inflated_wall.collidepoint(x, y):
                return False
            if wall_rect.collidepoint(x, y):
                return False

        for door_rect in self.doors:
            inflated_door = door_rect.inflate(agent_radius * 2, agent_radius * 2)
            if inflated_door.collidepoint(x, y):
                return False
            if door_rect.collidepoint(x, y):
                return False

        return True

    def find_safest_position(self, padding):
        """
        Fallback method to find a position likely furthest from obstacles by sampling grid points.

        Args:
            padding (float): Minimum distance from simulation boundaries.

        Returns:
            tuple: The (x, y) coordinates of the safest sampled position, or the center if none found.
        """
        grid_size = 20
        candidates = []
        obstacles = self.walls + self.doors

        for i in range(grid_size):
            for j in range(grid_size):
                x = padding + (self.width - 2 * padding) * i / (grid_size - 1)
                y = padding + (self.height - 2 * padding) * j / (grid_size - 1)

                min_distance = float('inf')
                inside_obstacle = False

                for obst_rect in obstacles:
                    if obst_rect.collidepoint(x, y):
                        inside_obstacle = True
                        break

                    clamped_x = max(obst_rect.left, min(x, obst_rect.right))
                    clamped_y = max(obst_rect.top, min(y, obst_rect.bottom))
                    dx = x - clamped_x
                    dy = y - clamped_y
                    distance = math.hypot(dx, dy)
                    min_distance = min(min_distance, distance)

                if inside_obstacle:
                    continue

                candidates.append((x, y, min_distance))

        if candidates:
            candidates.sort(key=lambda c: -c[2])
            print(f"Fallback: Chose safest position ({candidates[0][0]:.1f}, {candidates[0][1]:.1f})")
            return (candidates[0][0], candidates[0][1])
        else:
            print("Warning: No safe position found even with fallback, using center.")
            return (self.width / 2, self.height / 2)

    def remove_agent(self, agent, reason="died"):
        """
        Removes an agent from the simulation schedule and spatial grid, updating relevant counters.

        Args:
            agent (SchoolAgent): The agent instance to remove.
            reason (str, optional): The reason for removal ('died' or 'escaped'). Affects counters.
                                     Defaults to "died".
        """
        if agent in self.schedule:
            if reason == "died":
                if agent.agent_type == "student":
                    self.dead_student_count += 1
                elif agent.agent_type == "adult":
                    self.dead_adult_count += 1
                    if getattr(agent, 'has_weapon', False):
                        self.armed_adults_current -= 1
            elif reason == "escaped":
                if agent.agent_type == "student":
                    self.escaped_student_count += 1
                elif agent.agent_type == "adult" and getattr(agent, 'has_weapon', False):
                    self.armed_adults_current -= 1

            if agent in self.active_shooters:
                self.active_shooters.remove(agent)
                print(
                    f"Shooter {agent.unique_id} removed ({reason}). Active shooters left: {len(self.active_shooters)}")

            self.spatial_grid.remove_agent(agent)
            self.schedule.remove(agent)

    def collect_step_data(self):
        """
        Collects key statistics about the current state of the simulation model.

        Returns:
            dict: A dictionary containing simulation statistics for the current step (e.g., agent counts).
                  Returns None if data collection is throttled (optional, currently not implemented).
        """
        living_students = 0
        living_adults = 0
        living_armed_adults = 0
        living_unarmed_adults = 0
        living_shooters = 0

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


        current_living_shooters = len(self.active_shooters)

        total_dead_students = self.dead_student_count
        total_dead_adults = self.dead_adult_count

        total_escaped_students = self.escaped_student_count

        data = {
            "Time": round(self.simulation_time, 2),
            "Living Students": living_students,
            "Living Adults": living_adults,
            "Living Armed Adults": living_armed_adults,
            "Living Unarmed Adults": living_unarmed_adults,
            "Living Shooters": current_living_shooters,
            "Dead Students": total_dead_students,
            "Dead Adults": total_dead_adults,
            "Escaped Students": total_escaped_students
        }
        return data