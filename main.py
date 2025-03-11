from schoolmodel import SchoolModel
import time
import pygame

# Agent types
STUDENT = 0
ADULT = 1

# Simulation Parameters
N_STUDENTS = 526
N_ADULTS = 33
N_STUDENTS = 50
N_ADULTS = 20

# School dimensions - INCREASED SIZE with proper aspect ratio
SCHOOL_WIDTH = 600  # Match the aspect ratio of the screen (1.2:1)
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
    BLUE = (0, 0, 255)
    RED = (255, 0, 0)
    BLACK = (0, 0, 0)

    # Font voor tekst
    font = pygame.font.SysFont(None, 24)

    # Tijdvariabelen voor continue simulatie
    clock = pygame.time.Clock()
    last_update_time = time.time()
    current_time = time.time()
    simulation_time = 0.0  # Totale gesimuleerde tijd in seconden
    sim_speed = 1.0  # Simulatiesnelheid factor (1.0 = realtime)

    running = True
    while running:
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

        # Tijd berekenen
        current_time = time.time()
        dt = current_time - last_update_time  # Verstreken reële tijd sinds laatste update
        last_update_time = current_time

        # Gesimuleerde tijd bijwerken met snelheidsfactor
        sim_dt = dt * sim_speed
        simulation_time += sim_dt

        # Continue update van het model met delta tijd (in simulatie eenheden)
        # We delen door SECONDS_PER_STEP omdat elke 'stap' 5 seconden voorstelt
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

            # Kleur bepalen op basis van agent type
            color = BLUE if agent.agent_type == 'student' else RED

            # Agent tekenen als cirkel
            pygame.draw.circle(screen, color, (screen_x, screen_y), 4)  # Iets grotere cirkels voor de grotere scherm

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

        # Toon help informatie
        help_text = font.render("↑/↓: Speed up/down | Space: Reset speed", True, BLACK)
        screen.blit(help_text, (10, screen_height - 30))

        # Scherm updaten
        pygame.display.flip()

        # Framerate beperken tot 60 fps
        clock.tick(60)

    pygame.quit()


# Hoofdprogramma
if __name__ == "__main__":
    run_pygame_simulation()