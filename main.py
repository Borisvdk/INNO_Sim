import time
import pygame
import random
import csv
import os
from schoolmodel import SchoolModel
from visualization import Visualizer
from agents.studentagent import StudentAgent
from agents.adultagent import AdultAgent
from a_star import astar
import config

# --- CSV Configuration ---
CSV_FILENAME = "simulation_data.csv"
FIELDNAMES = [
    'Run', 'Time', 'Living Students', 'Living Adults',
    'Living Armed Adults', 'Living Unarmed Adults', 'Living Shooters',
    'Dead Students', 'Dead Adults', 'Escaped Students'
]
# -------------------------

def get_next_run_number(filename):
    """Reads the CSV to find the highest run number and returns the next one."""
    try:
        # Check if file exists and is not empty
        if not os.path.exists(filename) or os.path.getsize(filename) == 0:
            return 1 # Start with run 1 if file is new or empty

        with open(filename, 'r', newline='') as csvfile:
            # Use DictReader to easily access the 'Run' column
            reader = csv.DictReader(csvfile)
            # Ensure fieldnames are read correctly even if using DictReader just for last row
            if 'Run' not in reader.fieldnames:
                 print(f"Warning: 'Run' column not found in {filename}. Starting run count from 1.")
                 return 1

            max_run = 0
            # Efficiently get the last row's run number if file is large (optional)
            # For simplicity, we read all rows here, which is fine for moderate file sizes
            for row in reader:
                try:
                    run_num = int(row['Run'])
                    if run_num > max_run:
                        max_run = run_num
                except (ValueError, KeyError):
                    # Ignore rows with invalid or missing 'Run' number
                    continue
            return max_run + 1
    except FileNotFoundError:
        return 1
    except Exception as e:
        print(f"Error reading run number from {filename}: {e}. Starting run count from 1.")
        return 1

def run_pygame_simulation():
    """Main function to run the school simulation with visualization."""

    # --- Determine Run Number ---
    run_number = get_next_run_number(CSV_FILENAME)
    print(f"--- Starting Simulation Run: {run_number} ---")
    # --------------------------

    # Initialize model with parameters from config
    model = SchoolModel(
        n_students=config.INITIAL_STUDENTS,
        n_adults=config.INITIAL_ADULTS,
        width=config.SIM_WIDTH,
        height=config.SIM_HEIGHT,
        grid_file="grid.json"
    )

    # Pygame initialization
    pygame.init()

    # Load sound files - with error handling
    try:
        gunshot_sound = pygame.mixer.Sound("gunshot.wav")
        kill_sound = pygame.mixer.Sound("kill.wav")
        gunshot_sound.set_volume(0.5)
        kill_sound.set_volume(0.5)
        model.gunshot_sound = gunshot_sound
        model.kill_sound = kill_sound
    except pygame.error:
        print("Warning: Sound files not found. Continuing without sound.")
        # Create empty attributes to avoid attribute errors
        model.gunshot_sound = None
        model.kill_sound = None

    # Create visualizer with parameters from config
    screen_width, screen_height = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
    visualizer = Visualizer(model, screen_width=screen_width, screen_height=screen_height)

    # Time tracking variables
    clock = pygame.time.Clock()
    last_update_time = time.time()
    simulation_time = 0.0
    sim_speed = 1.0

    # FPS tracking with improved accuracy
    fps_samples = []
    fps_update_time = time.time()
    current_fps = 0

    # Visualization toggle flags
    show_line_of_sight = False
    show_safe_areas = False

    # --- Data Collection List ---
    simulation_run_data = []
    # Collect initial state (Time 0)
    initial_data = model.collect_step_data()
    if initial_data: # collect_step_data might return None if throttled
        initial_data['Run'] = run_number
        simulation_run_data.append(initial_data)
    # --------------------------

    # Main simulation loop
    running = True
    while running:
        frame_start_time = time.time()

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    sim_speed *= 2.0  # Double speed
                elif event.key == pygame.K_DOWN:
                    sim_speed /= 2.0  # Halve speed
                elif event.key == pygame.K_SPACE:
                    sim_speed = 1.0  # Reset to normal speed
                elif event.key == pygame.K_s:
                    # Add 10 students
                    model.add_students(10)
                elif event.key == pygame.K_a:
                    # Add 5 adults
                    model.add_adults(5)
                # Visualization toggle controls
                elif event.key == pygame.K_v:
                    show_line_of_sight = not show_line_of_sight
                    print(f"Line of sight visualization: {'ON' if show_line_of_sight else 'OFF'}")
                elif event.key == pygame.K_b:
                    show_safe_areas = not show_safe_areas
                    print(f"Safe areas visualization: {'ON' if show_safe_areas else 'OFF'}")
                elif event.key == pygame.K_x:  # New key for manually adding a shooter
                    success = model.add_manual_shooter()
                    if success:
                        visualizer.show_shooter_alert()
                        print("Manual shooter added to simulation!")

        # Time calculations
        current_time = time.time()
        dt = current_time - last_update_time
        last_update_time = current_time
        sim_dt = dt * sim_speed
        # simulation_time += sim_dt

        # Update model
        model.step_continuous(sim_dt)

        # Collect Data After Step
        step_data = model.collect_step_data()
        if step_data: # Handle potential throttling (if implemented)
            step_data['Run'] = run_number # Add run number to this step's data
            simulation_run_data.append(step_data)

        if model.should_terminate:
            print(f"Simulatie wordt beëindigd {config.TERMINATION_DELAY_AFTER_SHOOTER:.1f} seconden na de eerste schutter.")
            running = False
            # time.sleep(1)
            # continue

        # FPS calculation - improved moving average method
        current_frame_time = time.time() - frame_start_time
        if current_frame_time > 0:
            fps_samples.append(1.0 / current_frame_time)

            # Keep only recent samples (last ~0.5 seconds)
            if len(fps_samples) > 30:
                fps_samples.pop(0)

            # Update FPS every 0.25 seconds
            if time.time() - fps_update_time >= 0.25:
                if fps_samples:
                    current_fps = sum(fps_samples) / len(fps_samples)
                fps_update_time = time.time()

        # Render the current frame
        visualizer.render_frame(
            simulation_time=model.simulation_time,
            sim_speed=sim_speed,
            fps=current_fps,
            show_vision=show_line_of_sight,
            show_safe_areas=show_safe_areas
        )

        # Frame rate limiting
        clock.tick(config.FPS_LIMIT)
    
    # --- Write Data to CSV After Loop ---
    if simulation_run_data:
        print(f"Writing data for Run {run_number} to {CSV_FILENAME}...")
        file_exists = os.path.exists(CSV_FILENAME)
        try:
            with open(CSV_FILENAME, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)

                # Write header only if the file is new or empty
                if not file_exists or os.path.getsize(CSV_FILENAME) == 0:
                    writer.writeheader()

                writer.writerows(simulation_run_data)
            print(f"Successfully wrote {len(simulation_run_data)} data points.")
        except IOError as e:
            print(f"Error writing to CSV file {CSV_FILENAME}: {e}")
        except Exception as e:
             print(f"An unexpected error occurred during CSV writing: {e}")
    else:
        print("No simulation data collected to write.")

    pygame.quit()
    print(f"--- Simulation Run {run_number} Finished ---")

if __name__ == "__main__":
    run_pygame_simulation()