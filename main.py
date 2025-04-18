import time
import pygame
import csv
import os
import argparse
from schoolmodel import SchoolModel
from visualization import Visualizer
import config


CSV_FILENAME = "simulation_data_0%_Scream.csv"
FIELDNAMES = [
    'Run', 'Time', 'Living Students', 'Living Adults',
    'Living Armed Adults', 'Living Unarmed Adults', 'Living Shooters',
    'Dead Students', 'Dead Adults', 'Escaped Students'
]


def get_next_run_number(filename):
    """
    Reads a CSV file to determine the highest existing run number and returns the next sequential number.

    Args:
        filename (str): The path to the CSV file.

    Returns:
        int: The next available run number (starts from 1 if file doesn't exist or is invalid).
    """
    if not os.path.exists(filename):
        return 1
    try:
        with open(filename, 'r', newline='', encoding='utf-8') as csvfile:
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
                    if run_val and run_val.strip():
                        run_num = int(run_val)
                        max_run = max(max_run, run_num)
                except (ValueError, TypeError):
                    continue
            return max_run + 1
    except FileNotFoundError:
        return 1
    except Exception as e:
        print(f"Error reading run number from {filename}: {e}. Starting run count from 1.")
        return 1

def run_single_visual_simulation(run_number):
    """
    Initializes and runs a single instance of the school simulation with visualization,
    collecting data and writing it to a CSV file.

    Args:
        run_number (int): The unique identifier for this simulation run.
    """

    print(f"--- Starting Simulation Run: {run_number} ---")

    model = SchoolModel(
        n_students=config.INITIAL_STUDENTS,
        n_adults=config.INITIAL_ADULTS,
        width=config.SIM_WIDTH,
        height=config.SIM_HEIGHT,
        armed_adults_count=config.ARMED_ADULTS_COUNT,
        grid_file=config.GRID_FILE
    )

    pygame.init()
    pygame.mixer.init()

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

    visualizer = Visualizer(model, screen_width=config.SCREEN_WIDTH, screen_height=config.SCREEN_HEIGHT)

    clock = pygame.time.Clock()
    last_update_time = time.time()
    sim_speed = 1.0

    fps_samples = []
    fps_update_interval = 0.25
    fps_last_update = time.time()
    current_fps = 0

    show_vision = False
    show_ui = True

    simulation_run_data = []


    running = True
    while running:
        frame_start_time = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                     running = False
                elif event.key == pygame.K_UP:
                    sim_speed = min(sim_speed * 1.5, 64.0)
                elif event.key == pygame.K_DOWN:
                    sim_speed = max(sim_speed / 1.5, 0.125)
                elif event.key == pygame.K_SPACE:
                    sim_speed = 1.0
                elif event.key == pygame.K_s:
                    model.add_students(config.ADD_STUDENT_INCREMENT)
                elif event.key == pygame.K_a:
                    model.add_adults(config.ADD_ADULT_INCREMENT)
                elif event.key == pygame.K_x:
                    success = model.add_manual_shooter()
                    if success:
                        print("Manual shooter added to simulation!")
                    else:
                        print("Could not add manual shooter (maybe none available or max reached).")
                elif event.key == pygame.K_v:
                    show_vision = not show_vision
                    print(f"Shooter vision visualization: {'ON' if show_vision else 'OFF'}")
                elif event.key == pygame.K_h:
                    show_ui = not show_ui
                    print(f"UI Panels: {'Visible' if show_ui else 'Hidden'}")

        current_time = time.time()
        dt = min(current_time - last_update_time, 0.1)
        last_update_time = current_time
        sim_dt = dt * sim_speed

        model.step_continuous(sim_dt)

        step_data = model.collect_step_data()
        if step_data:
            step_data['Run'] = run_number
            simulation_run_data.append(step_data)

        if model.should_terminate:
            print(f"Simulation terminating for Run {run_number} (condition: {model.termination_reason}).")
            running = False
            visualizer.render_frame(
                simulation_time=model.simulation_time, sim_speed=sim_speed, fps=current_fps,
                show_vision=show_vision, show_ui=show_ui
            )
            pygame.display.flip()
            time.sleep(config.PAUSE_ON_TERMINATION)

        if not running:
            break

        frame_time = time.time() - frame_start_time
        if frame_time > 0:
            fps_samples.append(1.0 / frame_time)
            if len(fps_samples) > config.FPS_SAMPLE_COUNT:
                 fps_samples.pop(0)

            if time.time() - fps_last_update >= fps_update_interval:
                if fps_samples:
                    current_fps = sum(fps_samples) / len(fps_samples)
                fps_last_update = time.time()

        visualizer.render_frame(
            simulation_time=model.simulation_time,
            sim_speed=sim_speed,
            fps=current_fps,
            show_vision=show_vision,
            show_ui=show_ui
        )

        clock.tick(config.FPS_LIMIT)


    if simulation_run_data:
        print(f"Writing data for Run {run_number} to {CSV_FILENAME}...")
        file_exists = os.path.exists(CSV_FILENAME)
        is_empty = file_exists and os.path.getsize(CSV_FILENAME) == 0
        try:
            with open(CSV_FILENAME, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)

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

    visualizer.close()
    pygame.quit()
    print(f"--- Simulation Run {run_number} Finished ---")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run School Safety Simulation Sequentially with Visualization")
    parser.add_argument(
        '--runs',
        type=int,
        default=config.NUM_VISUAL_BATCH_RUNS,
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

            if i < num_simulations_to_run - 1 and config.PAUSE_BETWEEN_RUNS > 0:
                 print(f"Pausing for {config.PAUSE_BETWEEN_RUNS} seconds before next run...")
                 time.sleep(config.PAUSE_BETWEEN_RUNS)

        print(f"\n=== All {num_simulations_to_run} Visual Simulation Runs Completed ===")