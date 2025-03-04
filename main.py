from schoolmodel import SchoolModel

# Agent types
STUDENT = 0
ADULT = 1

# Simulation Parameters
N_STUDENTS = 526
N_ADULTS = 33

def run_pygame_simulation():
    """Simulatie met pygame voor betere realtime visualisatie."""
    import pygame

    # Maak een nieuw model
    model = SchoolModel(n_students=N_STUDENTS, n_adults=N_ADULTS, width=100, height=100)

    # Pygame initialiseren
    pygame.init()

    # Schermgrootte en schaling instellen
    screen_width, screen_height = 800, 800
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

    # Klok voor framerate
    clock = pygame.time.Clock()
    step_count = 0

    running = True
    while running:
        # Events afhandelen
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Simulatiestap uitvoeren
        model.step()
        step_count += 1

        # Scherm wissen
        screen.fill(WHITE)

        # Agenten tekenen
        for agent in model.schedule:
            x, y = agent.position

            # Schalen naar schermcoördinaten
            screen_x = int(x * scale_factor)
            screen_y = int(y * scale_factor)

            # Kleur bepalen op basis van agent type
            color = BLUE if agent.agent_type == STUDENT else RED

            # Agent tekenen als cirkel
            pygame.draw.circle(screen, color, (screen_x, screen_y), 5)

        # Toon stap nummer
        step_text = font.render(f"Step: {step_count}", True, BLACK)
        screen.blit(step_text, (10, 10))

        # Toon agent aantallen
        student_count = sum(1 for agent in model.schedule if agent.agent_type == STUDENT)
        adult_count = sum(1 for agent in model.schedule if agent.agent_type == ADULT)

        count_text = font.render(f"Students: {student_count}, Adults: {adult_count}", True, BLACK)
        screen.blit(count_text, (10, 40))

        # Scherm updaten
        pygame.display.flip()

        # Framerate beperken tot 30 fps
        clock.tick(30)

    pygame.quit()


# Hoofdprogramma
if __name__ == "__main__":
    run_pygame_simulation()
