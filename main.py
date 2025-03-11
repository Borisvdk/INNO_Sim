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
    """Simulatie met pygame met continue tijd."""
    import pygame

    # Maak een nieuw model met grotere afmetingen
    model = SchoolModel(n_students=N_STUDENTS, n_adults=N_ADULTS, width=SCHOOL_WIDTH, height=SCHOOL_HEIGHT)

    # Pygame initialiseren
    pygame.init()

    # Schermgrootte en schaling instellen
    screen_width, screen_height = 1200, 800
    scale_factor = min(screen_width / model.width, screen_height / model.height)

    # Pygame scherm maken
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("School Simulation")

    # Kleuren definiëren
    WHITE = (255, 255, 255)
    BLUE = (0, 0, 255)  # Students
    RED = (255, 0, 0)  # Adults
    BLACK = (0, 0, 0)  # Walls

    # Highlight colors for agents with weapons (if implemented)
    ARMED_STUDENT_COLOR = (100, 100, 255)  # Lighter blue
    ARMED_ADULT_COLOR = (255, 100, 100)  # Lighter red

    # Font voor tekst
    font = pygame.font.SysFont(None, 24)

    # Tijdvariabelen voor continue simulatie
    clock = pygame.time.Clock()
    last_update_time = time.time()
    current_time = time.time()
    simulation_time = 0.0  # Totale gesimuleerde tijd in seconden
    sim_speed = 1.0  # Simulatiesnelheid factor (1.0 = realtime)

    # Performance tracking
    frame_times = []
    last_fps_update = time.time()
    fps_update_interval = 1.0  # Update FPS display every second
    current_fps = 0.0  # Initialize FPS counter

    # Import needed classes here to avoid circular imports
    from agents.studentagent import StudentAgent
    from agents.adultagent import AdultAgent

    running = True
    while running:
        # Measure frame start time for performance tracking
        frame_start_time = time.time()

        # Events afhandelen
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # Simulatiesnelheid aanpassen met toetsen
                if event.key == pygame.K_UP:
                    sim_speed *= 2.0  # Verdubbel snelheid
                elif event.key == pygame.K_DOWN:
                    sim_speed /= 2.0  # Halveer snelheid
                elif event.key == pygame.K_SPACE:
                    # Reset naar normale snelheid
                    sim_speed = 1.0
                # Add student with 's' key
                elif event.key == pygame.K_s:
                    for _ in range(10):  # Add 10 students at once
                        x = random.uniform(5, model.width - 5)
                        y = random.uniform(5, model.height - 5)
                        student = StudentAgent(len(model.schedule), model, (x, y), "student", model.schedule)
                        model.schedule.append(student)
                # Add adult with 'a' key
                elif event.key == pygame.K_a:
                    for _ in range(5):  # Add 5 adults at once
                        x = random.uniform(5, model.width - 5)
                        y = random.uniform(5, model.height - 5)
                        adult = AdultAgent(len(model.schedule), model, (x, y), "adult", model.schedule)
                        model.schedule.append(adult)

        # Tijd berekenen
        current_time = time.time()
        dt = current_time - last_update_time  # Verstreken reële tijd sinds laatste update
        last_update_time = current_time

        # Gesimuleerde tijd bijwerken met snelheidsfactor
        sim_dt = dt * sim_speed
        simulation_time += sim_dt

        # Continue update van het model met delta tijd (in simulatie eenheden)
        model.step_continuous(sim_dt)

        # Scherm wissen
        screen.fill(WHITE)

        # Teken de muren
        for wall in model.walls:
            x_min, y_min, x_max, y_max = wall
            pygame.draw.rect(
                screen,
                BLACK,
                pygame.Rect(
                    x_min * scale_factor,
                    y_min * scale_factor,
                    (x_max - x_min) * scale_factor,
                    (y_max - y_min) * scale_factor
                )
            )

        # Agenten tekenen
        for agent in model.schedule:
            x, y = agent.position

            # Schalen naar schermcoördinaten
            screen_x = int(x * scale_factor)
            screen_y = int(y * scale_factor)

            # Determine color based on agent type and armed status
            if agent.agent_type == 'student':
                color = ARMED_STUDENT_COLOR if getattr(agent, 'has_weapon', False) else BLUE
            else:  # adult
                color = ARMED_ADULT_COLOR if getattr(agent, 'has_weapon', False) else RED

            # Draw agent as circle with proper radius
            # Use agent's actual radius from the physics model
            scaled_radius = int(agent.radius * scale_factor)
            pygame.draw.circle(screen, color, (screen_x, screen_y), scaled_radius)

            # Draw direction indicator (a small line showing where agent is heading)
            if hasattr(agent, 'velocity'):
                vx, vy = agent.velocity
                speed = math.sqrt(vx * vx + vy * vy)
                if speed > 0:
                    # Normalize and scale
                    direction_x = vx / speed * (scaled_radius + 2)
                    direction_y = vy / speed * (scaled_radius + 2)
                    pygame.draw.line(
                        screen,
                        (0, 0, 0),
                        (screen_x, screen_y),
                        (screen_x + direction_x, screen_y + direction_y),
                        1
                    )

        # Performance tracking
        frame_end_time = time.time()
        frame_time = frame_end_time - frame_start_time
        frame_times.append(frame_time)

        # Calculate FPS over the last second
        if current_time - last_fps_update > fps_update_interval:
            if frame_times:
                avg_frame_time = sum(frame_times) / len(frame_times)
                current_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
                frame_times = []  # Reset for next interval
                last_fps_update = current_time

        # Toon simulatie informatie
        time_text = font.render(f"Sim Time: {simulation_time:.1f}s", True, BLACK)
        screen.blit(time_text, (10, 10))

        # Toon simulatiesnelheid
        speed_text = font.render(f"Speed: {sim_speed:.1f}x", True, BLACK)
        screen.blit(speed_text, (10, 40))

        # Toon agent aantallen
        student_count = sum(1 for agent in model.schedule if agent.agent_type == 'student')
        adult_count = sum(1 for agent in model.schedule if agent.agent_type == 'adult')

        count_text = font.render(f"Students: {student_count}, Adults: {adult_count}", True, BLACK)
        screen.blit(count_text, (10, 70))

        # Display FPS
        fps_text = font.render(f"FPS: {current_fps:.1f}", True, BLACK)
        screen.blit(fps_text, (10, 100))

        # Toon help informatie
        help_text = font.render("↑/↓: Speed up/down | Space: Reset speed | S: Add students | A: Add adults", True,
                                BLACK)
        screen.blit(help_text, (10, screen_height - 30))

        # Scherm updaten
        pygame.display.flip()

        # Framerate beperken tot 60 fps
        clock.tick(60)

    pygame.quit()


# Hoofdprogramma
if __name__ == "__main__":
    run_pygame_simulation()