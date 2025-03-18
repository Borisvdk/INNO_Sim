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


def line_segments_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
    """
    Check if two line segments intersect.
    """
    # Calculate directions
    d1x = x2 - x1
    d1y = y2 - y1
    d2x = x4 - x3
    d2y = y4 - y3

    # Calculate the determinant
    determinant = d1x * d2y - d1y * d2x

    # If determinant is very close to zero, lines are parallel
    if abs(determinant) < 1e-8:
        return False

    # Calculate parameters for the intersection point
    s = ((x1 - x3) * d2y - (y1 - y3) * d2x) / determinant
    t = ((x1 - x3) * d1y - (y1 - y3) * d1x) / determinant

    # Check if the intersection is within both line segments
    return 0 <= s <= 1 and 0 <= t <= 1


def point_in_rectangle(x, y, rect_x1, rect_y1, rect_x2, rect_y2):
    """Check if a point is inside a rectangle."""
    return (rect_x1 <= x <= rect_x2 and rect_y1 <= y <= rect_y2)


def line_intersects_rectangle(line_x1, line_y1, line_x2, line_y2, rect_x1, rect_y1, rect_x2, rect_y2):
    """
    Check if a line intersects with a rectangle.
    """
    # Check if either endpoint is inside the rectangle
    if point_in_rectangle(line_x1, line_y1, rect_x1, rect_y1, rect_x2, rect_y2) or \
            point_in_rectangle(line_x2, line_y2, rect_x1, rect_y1, rect_x2, rect_y2):
        return True

    # Check if line intersects with any of the four edges of the rectangle
    rect_edges = [
        (rect_x1, rect_y1, rect_x2, rect_y1),  # Top edge
        (rect_x1, rect_y2, rect_x2, rect_y2),  # Bottom edge
        (rect_x1, rect_y1, rect_x1, rect_y2),  # Left edge
        (rect_x2, rect_y1, rect_x2, rect_y2)  # Right edge
    ]

    for edge_x1, edge_y1, edge_x2, edge_y2 in rect_edges:
        if line_segments_intersect(
                line_x1, line_y1, line_x2, line_y2,
                edge_x1, edge_y1, edge_x2, edge_y2
        ):
            return True

    return False


def visualize_line_of_sight(model, screen, scale_factor, shooter_agent=None):
    """
    Visualize the line of sight for the shooter agent.
    """
    # Find a shooter if none provided
    if shooter_agent is None:
        for agent in model.schedule:
            if hasattr(agent, 'is_shooter') and agent.is_shooter:
                shooter_agent = agent
                break

        if shooter_agent is None:
            return  # No shooter found

    # Get shooter position
    shooter_x, shooter_y = shooter_agent.position
    screen_shooter_x = int(shooter_x * scale_factor)
    screen_shooter_y = int(shooter_y * scale_factor)

    # Create a semi-transparent surface for lines
    temp_surface = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)

    # Visualize line of sight to all other agents
    for agent in model.schedule:
        if agent == shooter_agent:
            continue

        # Get agent position
        agent_x, agent_y = agent.position
        screen_agent_x = int(agent_x * scale_factor)
        screen_agent_y = int(agent_y * scale_factor)

        # Check line of sight
        has_sight = has_line_of_sight(shooter_agent.position, agent.position, model.walls)

        # Draw line with appropriate color
        if has_sight:
            # Draw a solid green line for visible agents
            pygame.draw.line(
                temp_surface,
                (0, 255, 0, 180),  # Semi-transparent green
                (screen_shooter_x, screen_shooter_y),
                (screen_agent_x, screen_agent_y),
                2
            )
        else:
            # Draw a semi-transparent red line for non-visible agents
            pygame.draw.line(
                temp_surface,
                (255, 0, 0, 64),  # Very transparent red
                (screen_shooter_x, screen_shooter_y),
                (screen_agent_x, screen_agent_y),
                1
            )

    # Blit the temporary surface to the screen
    screen.blit(temp_surface, (0, 0))


def has_line_of_sight(start_pos, end_pos, walls):
    """
    Check if there's a line of sight between start_pos and end_pos.

    Args:
        start_pos: Tuple (x, y) of the starting position
        end_pos: Tuple (x, y) of the ending position
        walls: List of wall coordinates (x_min, y_min, x_max, y_max)

    Returns:
        True if there's a clear line of sight, False if a wall blocks the view
    """
    start_x, start_y = start_pos
    end_x, end_y = end_pos

    # Check each wall for intersection
    for wall in walls:
        if line_intersects_rectangle(
                start_x, start_y, end_x, end_y,
                wall[0], wall[1], wall[2], wall[3]
        ):
            return False  # Wall blocks line of sight

    # No walls block the view
    return True


def visualize_safe_spawn_areas(model, screen, scale_factor):
    """
    Visualize the areas where agents can safely spawn (not in walls).
    """
    # Create a temporary surface for drawing with alpha
    temp_surface = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)

    # Sample a grid of points and check if they're in a wall
    grid_step = 10  # Controls the density of sampling points

    for x in range(0, model.width, grid_step):
        for y in range(0, model.height, grid_step):
            # Check if position is inside any wall
            is_in_wall = False
            for wall in model.walls:
                wall_x1, wall_y1, wall_x2, wall_y2 = wall
                if (wall_x1 <= x <= wall_x2 and wall_y1 <= y <= wall_y2):
                    is_in_wall = True
                    break

            # Convert to screen coordinates
            screen_x = int(x * scale_factor)
            screen_y = int(y * scale_factor)

            # Draw a dot
            color = (255, 0, 0, 100) if is_in_wall else (0, 255, 0, 40)  # Red for unsafe, green for safe
            radius = 3
            pygame.draw.circle(temp_surface, color, (screen_x, screen_y), radius)

    # Draw the surface
    screen.blit(temp_surface, (0, 0))


def run_pygame_simulation():
    """Optimized pygame simulation with visualization enhancements."""
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

    # Add visualization controls description
    viz_help_text = font.render(
        "V: Toggle Line of Sight | B: Toggle Safe Areas",
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
                # Visualization toggle controls
                elif event.key == pygame.K_v:
                    show_line_of_sight = not show_line_of_sight
                    print(f"Line of sight visualization: {'ON' if show_line_of_sight else 'OFF'}")
                elif event.key == pygame.K_b:
                    show_safe_areas = not show_safe_areas
                    print(f"Safe areas visualization: {'ON' if show_safe_areas else 'OFF'}")

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

        # Visualize safe areas if enabled
        if show_safe_areas:
            visualize_safe_spawn_areas(model, screen, scale_factor)

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

        # Visualize line of sight if enabled
        if show_line_of_sight:
            visualize_line_of_sight(model, screen, scale_factor)

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

        # Visualization status text
        los_status = "ON" if show_line_of_sight else "OFF"
        safe_status = "ON" if show_safe_areas else "OFF"
        viz_status_text = font.render(
            f"Line of Sight: {los_status} | Safe Areas: {safe_status}",
            True, COLORS["BLACK"]
        )

        # Draw UI text
        screen.blit(time_text, (10, 10))
        screen.blit(speed_text, (10, 40))
        screen.blit(count_text, (10, 70))
        screen.blit(fps_text, (10, 100))
        screen.blit(viz_status_text, (10, 130))
        screen.blit(help_text, (10, screen_height - 50))
        screen.blit(viz_help_text, (10, screen_height - 25))

        # Update display once per frame
        pygame.display.flip()

        # Frame rate limiting
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    run_pygame_simulation()