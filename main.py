from schoolmodel import SchoolModel
import time
import pygame
import math
import random

# Agent types
STUDENT = 0
ADULT = 1

# Simulation Parameters
N_STUDENTS = 100
N_ADULTS = 20

# School dimensions
SCHOOL_WIDTH = 600
SCHOOL_HEIGHT = 400


def run_pygame_simulation():
    """Optimized pygame simulation with continuous time."""
    # Import agent classes (to avoid circular imports)
    from agents.studentagent import StudentAgent
    from agents.adultagent import AdultAgent

    # Initialize model
    model = SchoolModel(n_students=N_STUDENTS, n_adults=N_ADULTS, width=SCHOOL_WIDTH, height=SCHOOL_HEIGHT)

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

    # Screen setup
    screen_width, screen_height = 1200, 800
    scale_factor = min(screen_width / model.width, screen_height / model.height)
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("School Shooter Simulation")

    # Pre-define colors for reuse
    COLORS = {
        "WHITE": (255, 255, 255),
        "BLUE": (0, 0, 255),
        "RED": (255, 0, 0),
        "BLACK": (0, 0, 0),
        "GREEN": (0, 255, 0),
        "ARMED_STUDENT": (100, 100, 255),
        "ARMED_ADULT": (255, 100, 100)
    }

    # Create a cached background with walls
    background = pygame.Surface((screen_width, screen_height))
    background.fill(COLORS["WHITE"])

    # Draw walls on background
    for wall in model.walls:
        x_min, y_min, x_max, y_max = wall
        pygame.draw.rect(
            background,
            COLORS["BLACK"],
            pygame.Rect(
                x_min * scale_factor,
                y_min * scale_factor,
                (x_max - x_min) * scale_factor,
                (y_max - y_min) * scale_factor
            )
        )

    # Create font and pre-render static UI text
    font = pygame.font.SysFont(None, 24)
    help_text = font.render(
        "↑/↓: Speed up/down | Space: Reset speed | S: Add students | A: Add adults",
        True, COLORS["BLACK"]
    )

    # Time tracking variables
    clock = pygame.time.Clock()
    last_update_time = time.time()
    simulation_time = 0.0
    sim_speed = 1.0
    shot_duration = 0.5

    # FPS tracking with improved accuracy
    fps_samples = []
    fps_update_time = time.time()
    current_fps = 0

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
                    # Add 10 students efficiently
                    for _ in range(10):
                        x = random.uniform(5, model.width - 5)
                        y = random.uniform(5, model.height - 5)
                        student = StudentAgent(len(model.schedule), model, (x, y), "student", model.schedule)
                        model.schedule.append(student)
                        model.spatial_grid.update_agent(student)
                elif event.key == pygame.K_a:
                    # Add 5 adults efficiently
                    for _ in range(5):
                        x = random.uniform(5, model.width - 5)
                        y = random.uniform(5, model.height - 5)
                        adult = AdultAgent(len(model.schedule), model, (x, y), "adult", model.schedule)
                        model.schedule.append(adult)
                        model.spatial_grid.update_agent(adult)

        # Time calculations
        current_time = time.time()
        dt = current_time - last_update_time
        last_update_time = current_time
        sim_dt = dt * sim_speed
        simulation_time += sim_dt

        # Update model - single step
        model.step_continuous(sim_dt)

        # Draw background (with walls)
        screen.blit(background, (0, 0))

        # Pre-calculate draw lists for batch rendering
        circles_to_draw = []
        lines_to_draw = []

        for agent in model.schedule:
            x, y = agent.position
            screen_x = int(x * scale_factor)
            screen_y = int(y * scale_factor)
            scaled_radius = int(agent.radius * scale_factor)

            # Determine color
            if agent.agent_type == "student":
                if getattr(agent, "is_shooter", False):
                    color = COLORS["GREEN"]
                elif getattr(agent, "has_weapon", False):
                    color = COLORS["ARMED_STUDENT"]
                else:
                    color = COLORS["BLUE"]
            else:  # adult
                color = COLORS["ARMED_ADULT"] if getattr(agent, "has_weapon", False) else COLORS["RED"]

            # Add circle to draw list
            circles_to_draw.append((color, (screen_x, screen_y), scaled_radius))

            # Add direction line to draw list if moving
            if hasattr(agent, "velocity"):
                vx, vy = agent.velocity
                speed_squared = vx * vx + vy * vy
                if speed_squared > 0.01:  # Only draw if moving at significant speed
                    speed = math.sqrt(speed_squared)
                    direction_x = vx / speed * (scaled_radius + 2)
                    direction_y = vy / speed * (scaled_radius + 2)
                    lines_to_draw.append(
                        (COLORS["BLACK"], (screen_x, screen_y),
                         (screen_x + direction_x, screen_y + direction_y), 1)
                    )

        # Draw all circles in batch
        for color, pos, radius in circles_to_draw:
            pygame.draw.circle(screen, color, pos, radius)

        # Draw all lines in batch
        for color, start, end, width in lines_to_draw:
            pygame.draw.line(screen, color, start, end, width)

        # Process and draw active shots efficiently
        current_sim_time = model.simulation_time
        shots_to_remove = []

        for i, shot in enumerate(model.active_shots):
            if current_sim_time - shot['start_time'] < shot_duration:
                # Scale shot coordinates
                start_x, start_y = shot['start_pos']
                end_x, end_y = shot['end_pos']
                screen_start = (int(start_x * scale_factor), int(start_y * scale_factor))
                screen_end = (int(end_x * scale_factor), int(end_y * scale_factor))
                pygame.draw.line(screen, (255, 0, 0), screen_start, screen_end, 2)
            else:
                shots_to_remove.append(i)

        # Remove expired shots - start from highest index to avoid shifting issues
        for i in sorted(shots_to_remove, reverse=True):
            if i < len(model.active_shots):
                model.active_shots.pop(i)

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

        # Count agents once for display
        student_count = sum(1 for agent in model.schedule if agent.agent_type == "student")
        adult_count = sum(1 for agent in model.schedule if agent.agent_type == "adult")

        # Render dynamic UI text
        time_text = font.render(f"Sim Time: {simulation_time:.1f}s", True, COLORS["BLACK"])
        speed_text = font.render(f"Speed: {sim_speed:.1f}x", True, COLORS["BLACK"])
        count_text = font.render(f"Students: {student_count}, Adults: {adult_count}", True, COLORS["BLACK"])
        fps_text = font.render(f"FPS: {current_fps:.1f}", True, COLORS["BLACK"])

        # Draw UI text
        screen.blit(time_text, (10, 10))
        screen.blit(speed_text, (10, 40))
        screen.blit(count_text, (10, 70))
        screen.blit(fps_text, (10, 100))
        screen.blit(help_text, (10, screen_height - 30))

        # Update display once per frame
        pygame.display.flip()

        # Frame rate limiting
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    run_pygame_simulation()