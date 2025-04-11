import time
import pygame
import random
import csv
import os
import argparse # Keep argparse to allow overriding run count
from schoolmodel import SchoolModel
from visualization import Visualizer
from agents.studentagent import StudentAgent
from agents.adultagent import AdultAgent
# from a_star import astar # Assuming used internally
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
    if not os.path.exists(filename):
        return 1
    try:
        with open(filename, 'r', newline='') as csvfile:
            # Handle empty file
            first_char = csvfile.read(1)
            if not first_char:
                return 1
            csvfile.seek(0)

            reader = csv.DictReader(csvfile)
            if 'Run' not in reader.fieldnames:
                 print(f"Warning: 'Run' column not found in {filename}. Starting run count from 1.")
                 return 1

            max_run = 0
            for row in reader:
                try:
                    run_val = row.get('Run')
                    if run_val is not None and run_val.strip():
                        run_num = int(run_val)
                        if run_num > max_run:
                            max_run = run_num
                except (ValueError, TypeError):
                    print(f"Warning: Skipping row with invalid 'Run' value: {row}")
                    continue
            return max_run + 1
    except FileNotFoundError:
        return 1
    except Exception as e:
        print(f"Error reading run number from {filename}: {e}. Starting run count from 1.")
        return 1

def run_single_visual_simulation(run_number):
    """Runs a single, visualized school simulation."""

    print(f"--- Starting Simulation Run: {run_number} ---")

    # Initialize model with parameters from config
    model = SchoolModel(
        n_students=config.INITIAL_STUDENTS,
        n_adults=config.INITIAL_ADULTS,
        width=config.SIM_WIDTH,
        height=config.SIM_HEIGHT,
        grid_file="grid.json"
    )

    # --- Pygame Initialization (Inside the function for each run) ---
    pygame.init()
    pygame.mixer.init() # Explicitly initialize mixer

    # Load sound files - with error handling
    try:
        gunshot_sound = pygame.mixer.Sound("gunshot.wav")
        kill_sound = pygame.mixer.Sound("kill.wav")
        gunshot_sound.set_volume(0.5)
        kill_sound.set_volume(0.5)
        model.gunshot_sound = gunshot_sound
        model.kill_sound = kill_sound
        print("Sound loaded successfully.")
    except pygame.error as e:
        print(f"Warning: Sound file error ({e}). Continuing without sound.")
        model.gunshot_sound = None
        model.kill_sound = None
    except FileNotFoundError:
         print(f"Warning: Sound file not found. Continuing without sound.")
         model.gunshot_sound = None
         model.kill_sound = None
    # --------------------------------------------------------------

    # Create visualizer with parameters from config
    screen_width, screen_height = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
    visualizer = Visualizer(model, screen_width=screen_width, screen_height=screen_height)

    # Time tracking variables
    clock = pygame.time.Clock()
    last_update_time = time.time()
    # simulation_time = 0.0 # Model handles its own time
    sim_speed = 1.0

    # FPS tracking
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
                if event.key == pygame.K_ESCAPE: # Add ESC key to quit
                     running = False
                elif event.key == pygame.K_UP:
                    sim_speed *= 2.0
                elif event.key == pygame.K_DOWN:
                    sim_speed /= 2.0
                elif event.key == pygame.K_SPACE:
                    sim_speed = 1.0
                elif event.key == pygame.K_s:
                    model.add_students(10)
                elif event.key == pygame.K_a:
                    model.add_adults(5)
                elif event.key == pygame.K_v:
                    show_line_of_sight = not show_line_of_sight
                    print(f"Line of sight visualization: {'ON' if show_line_of_sight else 'OFF'}")
                elif event.key == pygame.K_b:
                    show_safe_areas = not show_safe_areas
                    print(f"Safe areas visualization: {'ON' if show_safe_areas else 'OFF'}")
                elif event.key == pygame.K_x:
                    success = model.add_manual_shooter()
                    if success:
                        visualizer.show_shooter_alert()
                        print("Manual shooter added to simulation!")

        # Time calculations
        current_time = time.time()
        dt = current_time - last_update_time
        last_update_time = current_time
        sim_dt = dt * sim_speed

        # Update model
        model.step_continuous(sim_dt)

        # Collect Data After Step
        step_data = model.collect_step_data()
        if step_data: # Handle potential throttling (if implemented)
            step_data['Run'] = run_number # Add run number to this step's data
            simulation_run_data.append(step_data)

        if model.should_terminate:
            print(f"Simulation terminating for Run {run_number} (condition met).")
            running = False
            # Optional: Render one last frame before quitting
            visualizer.render_frame(
                simulation_time=model.simulation_time, sim_speed=sim_speed, fps=current_fps,
                show_vision=show_line_of_sight, show_safe_areas=show_safe_areas
            )
            pygame.display.flip() # Update the screen
            time.sleep(1.5) # Pause briefly to see final state
            # continue # Let the loop condition (running=False) handle exit

        # Prevent further processing if not running
        if not running:
            break

        # FPS calculation
        current_frame_time = time.time() - frame_start_time
        if current_frame_time > 0:
            fps_samples.append(1.0 / current_frame_time)
            if len(fps_samples) > 30: fps_samples.pop(0)
            if time.time() - fps_update_time >= 0.25:
                if fps_samples: current_fps = sum(fps_samples) / len(fps_samples)
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
                elif file_exists and os.path.getsize(CSV_FILENAME) > 0:
                     # Check if header exists if file is not empty
                     try:
                         with open(CSV_FILENAME, 'r', newline='', encoding='utf-8') as readfile:
                             # Read just enough to check the header
                             header_line = readfile.readline()
                             # Basic check if header matches expected fields
                             # This isn't foolproof but better than nothing
                             if not all(field in header_line for field in FIELDNAMES):
                                print(f"Warning: Header in {CSV_FILENAME} seems incorrect or missing. Writing header.")
                                # Reopen in append mode and write header (might duplicate if logic fails)
                                # Safer approach: If header mismatch is detected, maybe stop or rename the old file.
                                # For simplicity here, we'll assume the DictWriter handles it ok if header exists.
                                # Let's ensure the header is written ONLY if the file was truly empty above.
                                # The check above ensures we write if file is new OR size is 0.
                                pass
                     except Exception as read_e:
                         print(f"Could not read header from existing file: {read_e}. Assuming header exists.")


                writer.writerows(simulation_run_data)
            print(f"Successfully wrote {len(simulation_run_data)} data points for Run {run_number}.")
        except IOError as e:
            print(f"Error writing to CSV file {CSV_FILENAME} for Run {run_number}: {e}")
        except Exception as e:
             print(f"An unexpected error occurred during CSV writing for Run {run_number}: {e}")
    else:
        print(f"No simulation data collected for Run {run_number} to write.")

    # --- Pygame Quit (Inside the function for each run) ---
    pygame.quit()
    print(f"--- Simulation Run {run_number} Finished ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run School Shooting Simulation Sequentially with Visualization")
    parser.add_argument(
        '--runs',
        type=int,
        default=config.NUM_VISUAL_BATCH_RUNS, # Use the config value as default
        help=f'Number of sequential simulation runs with visualization (default: {config.NUM_VISUAL_BATCH_RUNS})'
    )

    args = parser.parse_args()
    num_simulations_to_run = args.runs

    print(f"\n=== Starting {num_simulations_to_run} Sequential Visual Simulation Runs ===")

    start_run_number = get_next_run_number(CSV_FILENAME)

    for i in range(num_simulations_to_run):
        current_run_number = start_run_number + i
        run_single_visual_simulation(run_number=current_run_number)
        # Optional short pause between visualized runs if desired
        if i < num_simulations_to_run - 1:
             print(f"Pausing briefly before next run...")
             time.sleep(2) # Pause for 2 seconds

    print(f"=== All {num_simulations_to_run} Visual Simulation Runs Completed ===")