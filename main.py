import time
import pygame
import csv
import os
import argparse
from schoolmodel import SchoolModel
from visualization import Visualizer
import config

# --- CSV Configuration ---
CSV_FILENAME = "simulation_data.csv"
# Ensure these match the keys returned by model.collect_step_data(), plus 'Run'
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
        with open(filename, 'r', newline='', encoding='utf-8') as csvfile:
            # Handle empty file
            first_char = csvfile.read(1)
            if not first_char:
                return 1
            csvfile.seek(0) # Reset file pointer

            reader = csv.DictReader(csvfile)
            # Basic check if 'Run' column exists in the header
            if 'Run' not in reader.fieldnames:
                 print(f"Warning: 'Run' column not found in {filename}. Starting run count from 1.")
                 return 1

            max_run = 0
            for row in reader:
                try:
                    # Safely get and parse the 'Run' value
                    run_val = row.get('Run')
                    if run_val and run_val.strip(): # Check if not None and not empty string
                        run_num = int(run_val)
                        max_run = max(max_run, run_num)
                except (ValueError, TypeError):
                    # Skip rows with invalid 'Run' values
                    # print(f"Warning: Skipping row with invalid 'Run' value: {row}") # Can be verbose
                    continue
            return max_run + 1
    except FileNotFoundError:
        return 1 # File doesn't exist, start from 1
    except Exception as e:
        # Catch other potential errors during file reading
        print(f"Error reading run number from {filename}: {e}. Starting run count from 1.")
        return 1

def run_single_visual_simulation(run_number):
    """Runs a single, visualized school simulation and collects data."""

    print(f"--- Starting Simulation Run: {run_number} ---")

    # Initialize model using config parameters
    model = SchoolModel(
        n_students=config.INITIAL_STUDENTS,
        n_adults=config.INITIAL_ADULTS,
        width=config.SIM_WIDTH,
        height=config.SIM_HEIGHT,
        armed_adults_count=config.ARMED_ADULTS_COUNT,
        grid_file=config.GRID_FILE
    )

    # Initialize Pygame and sound (inside the function for clean runs)
    pygame.init()
    pygame.mixer.init() # Initialize sound mixer

    # Load sounds with error handling
    try:
        gunshot_sound = pygame.mixer.Sound(config.GUNSHOT_SOUND_FILE)
        kill_sound = pygame.mixer.Sound(config.KILL_SOUND_FILE)
        gunshot_sound.set_volume(config.SOUND_VOLUME)
        kill_sound.set_volume(config.SOUND_VOLUME)
        model.gunshot_sound = gunshot_sound
        model.kill_sound = kill_sound
        print("Sounds loaded successfully.")
    except pygame.error as e:
        print(f"Warning: Pygame sound error ({e}). Files might be missing or corrupt. Continuing without sound.")
        model.gunshot_sound = None
        model.kill_sound = None
    except FileNotFoundError:
         print(f"Warning: Sound file(s) not found ({config.GUNSHOT_SOUND_FILE}, {config.KILL_SOUND_FILE}). Continuing without sound.")
         model.gunshot_sound = None
         model.kill_sound = None

    # Initialize visualizer using config parameters
    visualizer = Visualizer(model, screen_width=config.SCREEN_WIDTH, screen_height=config.SCREEN_HEIGHT)

    # Time tracking
    clock = pygame.time.Clock()
    last_update_time = time.time()
    sim_speed = 1.0

    # FPS tracking
    fps_samples = []
    fps_update_interval = 0.25 # Update FPS display every 0.25 seconds
    fps_last_update = time.time()
    current_fps = 0

    # Visualization state flags
    show_vision = False # For shooter vision cone
    show_ui = True      # For toggling UI panels

    # Data collection list for this run
    simulation_run_data = []
    # Collect initial state (Time 0) - model should handle time=0 data internally if needed
    # initial_data = model.collect_step_data() # Assuming model returns None if time is 0 or throttled
    # if initial_data:
    #     initial_data['Run'] = run_number
    #     simulation_run_data.append(initial_data)

    # Main simulation loop
    running = True
    while running:
        frame_start_time = time.time()

        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                     running = False
                # Speed controls
                elif event.key == pygame.K_UP:
                    sim_speed = min(sim_speed * 1.5, 64.0) # Limit max speed
                elif event.key == pygame.K_DOWN:
                    sim_speed = max(sim_speed / 1.5, 0.125) # Limit min speed
                elif event.key == pygame.K_SPACE:
                    sim_speed = 1.0
                # Agent adding controls
                elif event.key == pygame.K_s:
                    model.add_students(config.ADD_STUDENT_INCREMENT) # Use config value
                elif event.key == pygame.K_a:
                    model.add_adults(config.ADD_ADULT_INCREMENT)     # Use config value
                elif event.key == pygame.K_x:
                    success = model.add_manual_shooter()
                    if success:
                        # visualizer.show_shooter_alert() # Alert is now triggered internally by Visualizer based on model state
                        print("Manual shooter added to simulation!")
                    else:
                        print("Could not add manual shooter (maybe none available or max reached).")
                # Visualization toggles
                elif event.key == pygame.K_v:
                    show_vision = not show_vision
                    print(f"Shooter vision visualization: {'ON' if show_vision else 'OFF'}")
                elif event.key == pygame.K_h:
                    show_ui = not show_ui
                    print(f"UI Panels: {'Visible' if show_ui else 'Hidden'}")

        # --- Time Calculation ---
        current_time = time.time()
        # Ensure dt is not excessively large if paused or lagging
        dt = min(current_time - last_update_time, 0.1) # Max dt step of 0.1s wall-time
        last_update_time = current_time
        sim_dt = dt * sim_speed # Time step for the model simulation

        # --- Model Update ---
        model.step_continuous(sim_dt)

        # --- Data Collection (after step) ---
        step_data = model.collect_step_data() # Model might throttle data collection
        if step_data:
            step_data['Run'] = run_number # Tag data with the run number
            simulation_run_data.append(step_data)

        # --- Termination Check ---
        if model.should_terminate:
            print(f"Simulation terminating for Run {run_number} (condition: {model.termination_reason}).")
            running = False
            # Render one last frame before quitting and pause briefly
            visualizer.render_frame(
                simulation_time=model.simulation_time, sim_speed=sim_speed, fps=current_fps,
                show_vision=show_vision, show_ui=show_ui
            )
            pygame.display.flip()
            time.sleep(config.PAUSE_ON_TERMINATION) # Pause briefly from config

        # Prevent rendering/FPS calc if terminating
        if not running:
            break

        # --- FPS Calculation ---
        frame_time = time.time() - frame_start_time
        if frame_time > 0:
            fps_samples.append(1.0 / frame_time)
            # Keep only the last N samples for a smoother average
            if len(fps_samples) > config.FPS_SAMPLE_COUNT:
                 fps_samples.pop(0)

            # Update FPS value periodically
            if time.time() - fps_last_update >= fps_update_interval:
                if fps_samples:
                    current_fps = sum(fps_samples) / len(fps_samples)
                fps_last_update = time.time()

        # --- Rendering ---
        visualizer.render_frame(
            simulation_time=model.simulation_time,
            sim_speed=sim_speed,
            fps=current_fps,
            show_vision=show_vision,
            show_ui=show_ui  # Pass UI visibility state
        )

        # --- Frame Rate Limiting ---
        clock.tick(config.FPS_LIMIT) # Limit drawing speed

    # --- End of Simulation Run ---

    # Write collected data for this run to CSV
    if simulation_run_data:
        print(f"Writing data for Run {run_number} to {CSV_FILENAME}...")
        file_exists = os.path.exists(CSV_FILENAME)
        is_empty = file_exists and os.path.getsize(CSV_FILENAME) == 0
        try:
            # Use 'a' to append, create file if it doesn't exist
            with open(CSV_FILENAME, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)

                # Write header only if the file is brand new OR was empty
                if not file_exists or is_empty:
                    writer.writeheader()
                    print("CSV header written.")

                writer.writerows(simulation_run_data)
            print(f"Successfully wrote {len(simulation_run_data)} data points for Run {run_number}.")
        except IOError as e:
            print(f"Error writing to CSV file {CSV_FILENAME} for Run {run_number}: {e}")
        except Exception as e:
             print(f"An unexpected error occurred during CSV writing for Run {run_number}: {e}")
    else:
        print(f"No simulation data collected or suitable for writing for Run {run_number}.")

    # Clean up Pygame resources for this run
    visualizer.close() # Call the visualizer's cleanup method if it exists
    pygame.quit()
    print(f"--- Simulation Run {run_number} Finished ---")


# --- Main Execution Block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run School Safety Simulation Sequentially with Visualization")
    parser.add_argument(
        '--runs',
        type=int,
        default=config.NUM_VISUAL_BATCH_RUNS, # Default from config
        help=f'Number of sequential simulation runs with visualization (default: {config.NUM_VISUAL_BATCH_RUNS})'
    )
    args = parser.parse_args()
    num_simulations_to_run = args.runs

    if num_simulations_to_run <= 0:
        print("Number of runs must be positive.")
    else:
        print(f"\n=== Starting {num_simulations_to_run} Sequential Visual Simulation Runs ===")
        start_run_number = get_next_run_number(CSV_FILENAME)
        print(f"Starting with Run Number: {start_run_number}")

        for i in range(num_simulations_to_run):
            current_run_number = start_run_number + i
            run_single_visual_simulation(run_number=current_run_number)

            # Optional pause between visualized runs
            if i < num_simulations_to_run - 1 and config.PAUSE_BETWEEN_RUNS > 0:
                 print(f"Pausing for {config.PAUSE_BETWEEN_RUNS} seconds before next run...")
                 time.sleep(config.PAUSE_BETWEEN_RUNS)

        print(f"\n=== All {num_simulations_to_run} Visual Simulation Runs Completed ===")