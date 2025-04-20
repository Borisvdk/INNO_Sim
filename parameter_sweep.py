import argparse
import csv
import os
import time
import datetime
import json
from collections import defaultdict
import statistics
import copy
import sys

# Import from headless.py
from headless import run_headless_simulation, FIELDNAMES

# Default configuration file name
DEFAULT_CONFIG_FILE = "sweep_config.json"
FALLBACK_CONFIG_FILES = ["test_config.json", "parameter_config.json", "config.json"]


class ParameterSweep:
    """Manages running multiple simulation configurations with multiple runs per configuration."""

    def __init__(self, base_output_dir="results"):
        """
        Initialize the parameter sweep manager.

        Args:
            base_output_dir (str): Base directory for storing results
        """
        self.base_output_dir = base_output_dir
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(base_output_dir, f"sweep_{self.timestamp}")
        self.summary_data = []
        self.configs = []

        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"Created output directory: {self.output_dir}")

    def add_config(self, config_dict, runs=5, name=None):
        """
        Add a configuration to be tested.

        Args:
            config_dict (dict): Dictionary of parameter values
            runs (int): Number of runs for this configuration
            name (str, optional): Custom name for this configuration
        """
        # Create a shallow copy of the config_dict to avoid modifying the original
        config_dict = dict(config_dict)

        if name is None:
            # Generate a name based on the key parameters
            key_params = []
            for key, value in config_dict.items():
                key_params.append(f"{key}={value}")
            name = "_".join(key_params)

        config = {
            "params": config_dict,
            "runs": runs,
            "name": name
        }

        self.configs.append(config)
        print(f"Added configuration: {name} ({runs} runs)")
        return self

    def _create_args_for_config(self, config_dict):
        """
        Create an argparse.Namespace object from a configuration dictionary.

        Args:
            config_dict (dict): Dictionary of parameter values

        Returns:
            argparse.Namespace: Arguments object for the simulation
        """
        args = argparse.Namespace()

        # Set default values for all parameters
        args.students = None
        args.adults = None
        args.armed_adults = None
        args.shooter_probability = None
        args.time_limit = 300.0
        args.sim_speed = 10.0
        args.sampling_interval = 0.5
        args.pause_between_runs = 0
        args.grid_file = None
        args.output = None  # Will be set later

        # Update with values from config_dict
        for key, value in config_dict.items():
            setattr(args, key, value)

        return args

    def run_all(self):
        """
        Run all configurations with their specified number of runs.
        """
        start_time = time.time()
        config_count = len(self.configs)

        print(f"\n=== Starting Parameter Sweep with {config_count} configurations ===")

        # Create a results summary file
        summary_path = os.path.join(self.output_dir, "sweep_summary.csv")
        summary_fields = [
            'Config Name', 'Parameters', 'Runs',
            'Avg Dead Students', 'StdDev Dead Students',
            'Avg Dead Adults', 'StdDev Dead Adults',
            'Avg Escaped Students', 'StdDev Escaped Students',
            'Avg Shooters', 'Avg Simulation Time'
        ]

        with open(summary_path, 'w', newline='', encoding='utf-8') as summary_file:
            summary_writer = csv.DictWriter(summary_file, fieldnames=summary_fields)
            summary_writer.writeheader()

        # Run each configuration with its specified runs
        for i, config in enumerate(self.configs):
            config_name = config["name"]
            config_params = config["params"]
            num_runs = config["runs"]

            print(f"\n[{i + 1}/{config_count}] Running configuration: {config_name}")
            print(f"Parameters: {config_params}")
            print(f"Number of runs: {num_runs}")

            # Create output filename for this configuration
            config_output_file = os.path.join(self.output_dir, f"{config_name}.csv")

            # Create args for this configuration
            args = self._create_args_for_config(config_params)
            args.output = config_output_file
            args.runs = num_runs

            # Track statistics
            config_stats = defaultdict(list)
            all_run_data = []

            # Run all runs for this configuration
            print(f"Running {num_runs} simulations for configuration {config_name}...")

            for run in range(1, num_runs + 1):
                print(f"\nRun {run}/{num_runs} for configuration {config_name}")
                run_data = run_headless_simulation(run_number=run, args=args)
                all_run_data.extend(run_data)

                # Get the last data point for statistics
                if run_data:
                    final_data = run_data[-1]
                    config_stats['Dead Students'].append(final_data['Dead Students'])
                    config_stats['Dead Adults'].append(final_data['Dead Adults'])
                    config_stats['Escaped Students'].append(final_data['Escaped Students'])
                    config_stats['Living Shooters'].append(final_data['Living Shooters'])
                    config_stats['Time'].append(final_data['Time'])

            # Write all run data to the output file
            if all_run_data:
                with open(config_output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
                    writer.writeheader()
                    writer.writerows(all_run_data)
                print(f"Wrote {len(all_run_data)} data points to {config_output_file}")

            # Calculate summary statistics
            summary_entry = {
                'Config Name': config_name,
                'Parameters': json.dumps(config_params),
                'Runs': num_runs
            }

            for stat_name in ['Dead Students', 'Dead Adults', 'Escaped Students']:
                if config_stats[stat_name]:
                    avg = statistics.mean(config_stats[stat_name])
                    stddev = statistics.stdev(config_stats[stat_name]) if len(config_stats[stat_name]) > 1 else 0
                    summary_entry[f'Avg {stat_name}'] = round(avg, 2)
                    summary_entry[f'StdDev {stat_name}'] = round(stddev, 2)
                else:
                    summary_entry[f'Avg {stat_name}'] = 0
                    summary_entry[f'StdDev {stat_name}'] = 0

            summary_entry['Avg Shooters'] = round(statistics.mean(config_stats['Living Shooters'])) if config_stats[
                'Living Shooters'] else 0
            summary_entry['Avg Simulation Time'] = round(statistics.mean(config_stats['Time']), 1) if config_stats[
                'Time'] else 0

            # Append to summary data
            self.summary_data.append(summary_entry)

            # Update the summary file after each configuration
            with open(summary_path, 'a', newline='', encoding='utf-8') as summary_file:
                summary_writer = csv.DictWriter(summary_file, fieldnames=summary_fields)
                summary_writer.writerow(summary_entry)

        # Print final summary
        elapsed_time = time.time() - start_time
        print(f"\n=== Parameter Sweep Complete ===")
        print(f"Total configurations: {config_count}")
        print(f"Total time: {elapsed_time:.1f} seconds")
        print(f"Results saved to: {self.output_dir}")
        print(f"Summary file: {summary_path}")

        return self.summary_data


def create_parameter_grid(param_ranges):
    """
    Create all combinations of parameters based on provided ranges.

    Args:
        param_ranges (dict): Dictionary mapping parameter names to lists of values

    Returns:
        list: List of dictionaries, each representing a parameter combination
    """
    param_names = list(param_ranges.keys())
    combinations = []

    def generate_combinations(index, current_combo):
        if index == len(param_names):
            combinations.append(copy.deepcopy(current_combo))
            return

        param = param_names[index]
        values = param_ranges[param]

        for value in values:
            current_combo[param] = value
            generate_combinations(index + 1, current_combo)

    generate_combinations(0, {})
    return combinations


def find_config_file(specified_file=None):
    """
    Locate a suitable configuration file.
    Order of precedence:
    1. Specified file from command line
    2. Default config file (sweep_config.json)
    3. Any of the fallback config files

    Args:
        specified_file (str, optional): Explicitly specified config file path

    Returns:
        str or None: Path to the found config file, or None if none found
    """
    # Check for explicitly specified file
    if specified_file and os.path.exists(specified_file) and os.path.isfile(specified_file):
        print(f"Using specified configuration file: {specified_file}")
        return specified_file

    # Check for default config file
    if os.path.exists(DEFAULT_CONFIG_FILE) and os.path.isfile(DEFAULT_CONFIG_FILE):
        print(f"Using default configuration file: {DEFAULT_CONFIG_FILE}")
        return DEFAULT_CONFIG_FILE

    # Try fallback config files
    for fallback_file in FALLBACK_CONFIG_FILES:
        if os.path.exists(fallback_file) and os.path.isfile(fallback_file):
            print(f"Using fallback configuration file: {fallback_file}")
            return fallback_file

    # No config file found
    return None


def load_configurations(sweep, config_file, debug=False):
    """
    Load configurations from a JSON file and add them to the sweep object.

    Args:
        sweep (ParameterSweep): The parameter sweep object
        config_file (str): Path to the configuration file
        debug (bool): Whether to enable debug output

    Returns:
        bool: True if configurations were successfully loaded, False otherwise
    """
    try:
        with open(config_file, 'r') as f:
            file_content = f.read()

            if debug:
                print(f"File content: {file_content}")

            try:
                config_data = json.loads(file_content)
            except json.JSONDecodeError as e:
                print(f"ERROR: Invalid JSON in configuration file: {e}")
                return False

            # Check for parameter grid mode
            if 'parameter_grid' in config_data:
                grid_params = config_data['parameter_grid']
                runs_per_config = config_data.get('runs_per_config', 5)

                print(f"Generating parameter grid from {len(grid_params)} parameters...")
                if debug:
                    print(f"Parameter grid: {grid_params}")

                combinations = create_parameter_grid(grid_params)
                print(f"Generated {len(combinations)} parameter combinations")

                for combo in combinations:
                    if debug:
                        print(f"Adding combination: {combo}")
                    sweep.add_config(combo, runs=runs_per_config)

                return True

            # Check for explicit configurations
            elif 'configurations' in config_data:
                configs = config_data['configurations']
                print(f"Loading {len(configs)} explicit configurations...")

                for config in configs:
                    params = config['params']
                    runs = config.get('runs', 5)
                    name = config.get('name', None)

                    if debug:
                        print(f"Adding configuration: {name} - {params}")

                    sweep.add_config(params, runs=runs, name=name)

                return True

            else:
                print("ERROR: Config file must contain either 'parameter_grid' or 'configurations'")
                return False

    except Exception as e:
        print(f"ERROR: Failed to load configuration file: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return False


def add_default_configs(sweep):
    """Add default configurations to the sweep object when no config file is found."""
    print("No configuration file found. Using default configurations.")

    # Example 1: No armed adults
    sweep.add_config(
        {
            'students': 50,
            'adults': 5,
            'armed_adults': 0,
            'shooter_probability': 0.01,
            'time_limit': 300
        },
        runs=5,
        name="no_armed_adults"
    )

    # Example 2: Some armed adults
    sweep.add_config(
        {
            'students': 50,
            'adults': 5,
            'armed_adults': 3,
            'shooter_probability': 0.01,
            'time_limit': 300
        },
        runs=5,
        name="three_armed_adults"
    )

    # Example 3: Fully armed adults
    sweep.add_config(
        {
            'students': 50,
            'adults': 5,
            'armed_adults': 5,
            'shooter_probability': 0.01,
            'time_limit': 300
        },
        runs=5,
        name="all_armed_adults"
    )


# Example usage as a script
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run parameter sweep for school safety simulation")
    parser.add_argument('--config', type=str, help='Optional: Custom configuration JSON file path')
    parser.add_argument('--output-dir', type=str, default='results', help='Base output directory')
    parser.add_argument('--debug', action='store_true', help='Enable verbose debug output')
    args = parser.parse_args()

    # Initialize the parameter sweep
    sweep = ParameterSweep(args.output_dir)

    # Find appropriate config file
    config_file = find_config_file(args.config)

    if config_file:
        # Load configurations from file
        success = load_configurations(sweep, config_file, args.debug)
        if not success:
            print("Failed to load configurations from file. Using defaults instead.")
            add_default_configs(sweep)
    else:
        # No config file found, use defaults
        add_default_configs(sweep)

    # Verify we have configurations
    if not sweep.configs:
        print("ERROR: No configurations were defined. Exiting.")
        sys.exit(1)

    print(f"\nTotal configurations to run: {len(sweep.configs)}")
    for config in sweep.configs:
        print(f"  - {config['name']}: {config['params']} ({config['runs']} runs)")

    # Run all configurations
    sweep.run_all()