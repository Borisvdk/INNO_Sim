import time
import csv
import os
import argparse
from schoolmodel import SchoolModel
import config
import pygame

# Initialize pygame only for its math functionality, not display
pygame.init()

# CSV output configuration
DEFAULT_CSV_FILENAME = "headless_simulation_data.csv"
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


def run_headless_simulation(run_number, args):
    """
    Run a single headless simulation without visualization.

    Args:
        run_number (int): The unique identifier for this simulation run
        args (argparse.Namespace): Command line arguments

    Returns:
        list: Collected simulation data
    """
    print(f"--- Starting Headless Simulation Run: {run_number} ---")

    model = SchoolModel(
        n_students=args.students if args.students is not None else config.INITIAL_STUDENTS,
        n_adults=args.adults if args.adults is not None else config.INITIAL_ADULTS,
        width=config.SIM_WIDTH,
        height=config.SIM_HEIGHT,
        armed_adults_count=args.armed_adults if args.armed_adults is not None else config.ARMED_ADULTS_COUNT,
        grid_file=args.grid_file if args.grid_file is not None else config.GRID_FILE
    )

    # Disable sound effects in headless mode
    model.gunshot_sound = None
    model.kill_sound = None

    # Set shooter emergence probability
    if args.shooter_probability is not None:
        model.shooter_emergence_probability = args.shooter_probability

    # Set simulation time limit
    sim_time_limit = args.time_limit if args.time_limit is not None else 300.0  # Default 5 minutes

    # Set simulation speed
    sim_speed = args.sim_speed if args.sim_speed is not None else 10.0  # Default 10x speed

    # Track the last time data was collected for sampling
    last_data_time = 0
    data_sampling_interval = args.sampling_interval if args.sampling_interval is not None else 0.5

    simulation_run_data = []
    running = True
    last_update_time = time.time()

    print(f"  Configuration: {model.num_students} students, {model.num_adults} adults, "
          f"{model.armed_adults_count} armed adults, Speed: {sim_speed}x")
    print(f"  Time limit: {sim_time_limit}s, Data sampling: every {data_sampling_interval}s")

    while running:
        # Calculate real time delta
        current_time = time.time()
        dt = min(current_time - last_update_time, 0.1)  # Cap at 100ms to prevent large jumps
        last_update_time = current_time

        # Apply simulation speed factor
        sim_dt = dt * sim_speed

        # Step the simulation
        model.step_continuous(sim_dt)

        # Collect data at regular intervals
        if model.simulation_time - last_data_time >= data_sampling_interval:
            step_data = model.collect_step_data()
            if step_data:
                step_data['Run'] = run_number
                simulation_run_data.append(step_data)
                last_data_time = model.simulation_time

        # Check termination conditions
        if model.should_terminate:
            print(f"  Simulation terminating for Run {run_number} (condition: {model.termination_reason}).")
            running = False

        # Time limit check
        if model.simulation_time >= sim_time_limit:
            model.terminate_simulation = True
            model.termination_reason = f"Reached time limit ({sim_time_limit}s)"
            print(f"  Simulation reached time limit ({sim_time_limit}s).")
            running = False

        # Progress indicator (print every ~10% of time limit)
        progress_step = sim_time_limit / 10
        if int(model.simulation_time / progress_step) > int(last_data_time / progress_step):
            progress_pct = min(100, int(model.simulation_time / sim_time_limit * 100))
            print(f"  Progress: {progress_pct}% - Simulation time: {model.simulation_time:.1f}s")

    # Collect final statistics
    final_stats = model.collect_step_data()
    if final_stats:
        final_stats['Run'] = run_number
        simulation_run_data.append(final_stats)

    # Print summary
    print(f"  Results: {final_stats['Dead Students']} students dead, "
          f"{final_stats['Dead Adults']} adults dead, "
          f"{final_stats['Escaped Students']} students escaped")
    print(f"  Collected {len(simulation_run_data)} data points over {model.simulation_time:.1f} seconds")
    print(f"--- Simulation Run {run_number} Finished ---")

    return simulation_run_data


def run_batch_simulations(args):
    """
    Run multiple headless simulations in batch mode.

    Args:
        args (argparse.Namespace): Command line arguments
    """
    csv_filename = args.output if args.output else DEFAULT_CSV_FILENAME
    num_simulations = args.runs if args.runs else 1

    print(f"\n=== Starting {num_simulations} Headless Simulation Runs ===")
    start_run_number = get_next_run_number(csv_filename)
    print(f"Starting with Run Number: {start_run_number}")
    print(f"Output file: {csv_filename}")

    batch_start_time = time.time()
    all_simulation_data = []

    for i in range(num_simulations):
        current_run_number = start_run_number + i
        run_data = run_headless_simulation(run_number=current_run_number, args=args)
        all_simulation_data.extend(run_data)

        if i < num_simulations - 1:
            if args.pause_between_runs:
                pause_time = args.pause_between_runs
                print(f"Pausing for {pause_time} seconds before next run...")
                time.sleep(pause_time)

    # Write all data to CSV
    if all_simulation_data:
        print(f"\nWriting data to {csv_filename}...")
        file_exists = os.path.exists(csv_filename)
        is_empty = file_exists and os.path.getsize(csv_filename) == 0

        try:
            with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)

                if not file_exists or is_empty:
                    writer.writeheader()

                writer.writerows(all_simulation_data)
            print(f"Successfully wrote {len(all_simulation_data)} data points.")
        except IOError as e:
            print(f"Error writing to CSV file {csv_filename}: {e}")
    else:
        print("No simulation data was collected.")

    batch_end_time = time.time()
    total_time = batch_end_time - batch_start_time
    print(f"\n=== All {num_simulations} Simulation Runs Completed in {total_time:.1f} seconds ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run School Safety Simulation in Headless Mode")

    # Basic configuration
    parser.add_argument('--runs', type=int, default=1, help='Number of simulation runs (default: 1)')
    parser.add_argument('--output', type=str, help=f'Output CSV filename (default: {DEFAULT_CSV_FILENAME})')
    parser.add_argument('--grid-file', type=str, help=f'Grid JSON file path (default: {config.GRID_FILE})')

    # Simulation parameters
    parser.add_argument('--students', type=int, help=f'Initial number of students (default: {config.INITIAL_STUDENTS})')
    parser.add_argument('--adults', type=int, help=f'Initial number of adults (default: {config.INITIAL_ADULTS})')
    parser.add_argument('--armed-adults', type=int,
                        help=f'Number of armed adults (default: {config.ARMED_ADULTS_COUNT})')
    parser.add_argument('--shooter-probability', type=float,
                        help=f'Probability of shooter emergence (default: {config.SHOOTER_EMERGENCE_PROBABILITY})')

    # Runtime parameters
    parser.add_argument('--time-limit', type=float, default=300.0,
                        help='Maximum simulation time in seconds (default: 300)')
    parser.add_argument('--sim-speed', type=float, default=10.0, help='Simulation speed multiplier (default: 10)')
    parser.add_argument('--sampling-interval', type=float, default=0.5,
                        help='Data collection interval in simulation seconds (default: 0.5)')
    parser.add_argument('--pause-between-runs', type=float, default=0,
                        help='Pause between simulation runs in seconds (default: 0)')

    args = parser.parse_args()
    run_batch_simulations(args)