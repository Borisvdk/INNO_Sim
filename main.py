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
    """Simulatie met pygame met continue tijd, inclusief een shooter."""
    import pygame

    # Maak een nieuw model met grotere afmetingen en een shooter
    model = SchoolModel(n_students=N_STUDENTS, n_adults=N_ADULTS, width=SCHOOL_WIDTH, height=SCHOOL_HEIGHT)

    # Pygame initialiseren
    pygame.init()

    # Load sound files
    gunshot_sound = pygame.mixer.Sound("gunshot.wav")
    kill_sound = pygame.mixer.Sound("kill.wav")

    # Optional: Adjust volume (0.0 = silent, 1.0 = full volume)
    gunshot_sound.set_volume(0.5)  # 50% volume
    kill_sound.set_volume(0.5)  # 50% volume

    # Attach sounds to the model for agent access
    model.gunshot_sound = gunshot_sound
    model.kill_sound = kill_sound

    # Schermgrootte en schaling instellen
    screen_width, screen_height = 1200, 800
    scale_factor = min(screen_width / model.width, screen_height / model.height)

    # Pygame scherm maken
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("School Shooter Simulation")

    # Kleuren definiëren
    WHITE = (255, 255, 255)
    BLUE = (0, 0, 255)  # Normale studenten
    RED = (255, 0, 0)  # Volwassenen
    BLACK = (0, 0, 0)  # Muren
    GREEN = (0, 255, 0)  # Shooter (onderscheiden van andere agenten)
    ARMED_STUDENT_COLOR = (100, 100, 255)  # Lichter blauw voor gewapende studenten (niet-shooter)
    ARMED_ADULT_COLOR = (255, 100, 100)  # Lichter rood voor gewapende volwassenen

    # Font voor tekst
    font = pygame.font.SysFont(None, 24)

    # Tijdvariabelen voor continue simulatie
    clock = pygame.time.Clock()
    last_update_time = time.time()
    current_time = time.time()
    simulation_time = 0.0  # Totale gesimuleerde tijd in seconden
    sim_speed = 1.0  # Simulatiesnelheid factor (1.0 = realtime)
    shot_duration = 0.5  # Display each shot for 0.5 seconds in simulation time

    # Performance tracking
    fps_samples = []
    fps_update_time = time.time()
    current_fps = 0

    # Importeer klassen om circulaire imports te vermijden
    from agents.studentagent import StudentAgent
    from agents.adultagent import AdultAgent

    running = True
    while running:
        # Meet frametijd voor performance tracking
        frame_start_time = time.time()

        # Events afhandelen
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    sim_speed *= 2.0  # Verdubbel snelheid
                elif event.key == pygame.K_DOWN:
                    sim_speed /= 2.0  # Halveer snelheid
                elif event.key == pygame.K_SPACE:
                    sim_speed = 1.0  # Reset naar normale snelheid
                elif event.key == pygame.K_s:
                    for _ in range(10):  # Voeg 10 studenten toe
                        x = random.uniform(5, model.width - 5)
                        y = random.uniform(5, model.height - 5)
                        student = StudentAgent(len(model.schedule), model, (x, y), "student", model.schedule)
                        model.schedule.append(student)
                elif event.key == pygame.K_a:
                    for _ in range(5):  # Voeg 5 volwassenen toe
                        x = random.uniform(5, model.width - 5)
                        y = random.uniform(5, model.height - 5)
                        adult = AdultAgent(len(model.schedule), model, (x, y), "adult", model.schedule)
                        model.schedule.append(adult)

        # Tijd berekenen
        current_time = time.time()
        dt = current_time - last_update_time
        last_update_time = current_time

        # Gesimuleerde tijd bijwerken met snelheidsfactor
        sim_dt = dt * sim_speed
        simulation_time += sim_dt

        # Continue update van het model
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
            screen_x = int(x * scale_factor)
            screen_y = int(y * scale_factor)
            scaled_radius = int(agent.radius * scale_factor)

            # Bepaal kleur gebaseerd op agenttype en status
            if agent.agent_type == "student":
                if getattr(agent, "is_shooter", False):
                    color = GREEN  # Shooter in groen
                elif getattr(agent, "has_weapon", False):
                    color = ARMED_STUDENT_COLOR
                else:
                    color = BLUE
            else:  # adult
                color = ARMED_ADULT_COLOR if getattr(agent, "has_weapon", False) else RED

            # Teken agent als cirkel
            pygame.draw.circle(screen, color, (screen_x, screen_y), scaled_radius)

            # Teken richtingaanwijzer
            if hasattr(agent, "velocity"):
                vx, vy = agent.velocity
                speed = math.sqrt(vx * vx + vy * vy)
                if speed > 0:
                    direction_x = vx / speed * (scaled_radius + 2)
                    direction_y = vy / speed * (scaled_radius + 2)
                    pygame.draw.line(
                        screen,
                        BLACK,
                        (screen_x, screen_y),
                        (screen_x + direction_x, screen_y + direction_y),
                        1
                    )

        # Draw active shots
        current_time = model.simulation_time
        for shot in model.active_shots[:]:  # Use a copy to allow removal during iteration
            if current_time - shot['start_time'] < shot_duration:
                # Extract positions
                start_x, start_y = shot['start_pos']
                end_x, end_y = shot['end_pos']
                # Scale to screen coordinates
                screen_start = (int(start_x * scale_factor), int(start_y * scale_factor))
                screen_end = (int(end_x * scale_factor), int(end_y * scale_factor))
                # Draw a red line
                pygame.draw.line(screen, (255, 0, 0), screen_start, screen_end, 2)
            else:
                # Remove expired shots
                model.active_shots.remove(shot)

        current_frame_time = time.time() - frame_start_time
        fps_samples.append(1.0 / current_frame_time if current_frame_time > 0 else 0)

        # Keep only recent samples (last ~0.5 seconds)
        if len(fps_samples) > 30:
            fps_samples.pop(0)

        # Update FPS every 0.25 seconds
        if time.time() - fps_update_time >= 0.25:
            if fps_samples:
                current_fps = sum(fps_samples) / len(fps_samples)
            fps_update_time = time.time()

        # Toon simulatie-informatie
        time_text = font.render(f"Sim Time: {simulation_time:.1f}s", True, BLACK)
        screen.blit(time_text, (10, 10))
        speed_text = font.render(f"Speed: {sim_speed:.1f}x", True, BLACK)
        screen.blit(speed_text, (10, 40))
        student_count = sum(1 for agent in model.schedule if agent.agent_type == "student")
        adult_count = sum(1 for agent in model.schedule if agent.agent_type == "adult")
        count_text = font.render(f"Students: {student_count}, Adults: {adult_count}", True, BLACK)
        screen.blit(count_text, (10, 70))
        fps_text = font.render(f"FPS: {current_fps:.1f}", True, BLACK)
        screen.blit(fps_text, (10, 100))
        help_text = font.render("↑/↓: Speed up/down | Space: Reset speed | S: Add students | A: Add adults", True,
                                BLACK)
        screen.blit(help_text, (10, screen_height - 30))

        # Scherm updaten
        pygame.display.flip()

        # Framerate beperken
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    run_pygame_simulation()
