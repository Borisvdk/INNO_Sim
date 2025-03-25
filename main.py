import time
import pygame
import random
from schoolmodel import SchoolModel
from visualization import Visualizer
from agents.studentagent import StudentAgent
from agents.adultagent import AdultAgent
from dijkstra_test import astar
import config

def run_pygame_simulation():
    """Main function to run the school simulation with visualization."""

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
    emergency = False

    # FPS tracking with improved accuracy
    fps_samples = []
    fps_update_time = time.time()
    current_fps = 0

    # Visualization toggle flags
    show_line_of_sight = False
    show_safe_areas = False

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
        simulation_time += sim_dt

        # Update model
        model.step_continuous(sim_dt)

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
            simulation_time=simulation_time,
            sim_speed=sim_speed,
            fps=current_fps,
            show_line_of_sight=show_line_of_sight,
            show_safe_areas=show_safe_areas
        )

        # Frame rate limiting
        clock.tick(config.FPS_LIMIT)

    pygame.quit()

if __name__ == "__main__":
    run_pygame_simulation()