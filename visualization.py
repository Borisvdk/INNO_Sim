import pygame
import math
import time
from utilities import cast_ray
import config


class Visualizer:
    """Visualization system for the school simulation model."""

    def __init__(self, model, screen_width=config.SCREEN_WIDTH, screen_height=config.SCREEN_HEIGHT):
        """Initialize the visualization system."""
        self.model = model
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.scale_factor = min(screen_width / model.width, screen_height / model.height)

        # Initialize Pygame screen
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("School Safety Simulation")

        # Use colors from config
        self.COLORS = config.COLORS
        # Add default colors if missing
        defaults = {
            "BROWN": (139, 69, 19),
            "PANEL_BG": (50, 50, 50, 180), # Semi-transparent dark gray
            "TEXT_COLOR": (240, 240, 240), # Light gray/white
            "ALERT": (255, 0, 0),
            "WHITE": (255, 255, 255),
            "BLACK": (0, 0, 0),
            "BLUE": (0, 0, 255),
            "RED": (200, 0, 0), # Slightly less bright red for adults
            "GREEN": (0, 150, 0), # Shooter color
            "ARMED_STUDENT": (100, 100, 255), # Lighter blue
            "ARMED_ADULT": (255, 255, 0), # Yellow
            "AWARE_ADULT": (255, 100, 0), # Orange
            "FLEEING_STUDENT": (0, 100, 255), # Darker blue
            "SCREAM_FILL": (255, 165, 0, 30), # Fainter orange fill
            "SCREAM_OUTLINE": (255, 165, 0, 60), # Fainter orange outline
            "SHOT": (255, 0, 0),
            "EXIT_FILL": (0, 200, 0, 80), # Semi-transparent green
            "EXIT_BORDER": (0, 100, 0, 150) # Darker green border
        }
        for key, value in defaults.items():
            self.COLORS.setdefault(key, value)


        # Create cached background with walls and doors
        self._create_cached_background()

        # Prepare fonts for UI elements (smaller sizes)
        self.ui_font_size = 18
        self.help_font_size = 16
        self.alert_font_size = 28
        try:
            self.ui_font = pygame.font.SysFont(None, self.ui_font_size)
            self.help_font = pygame.font.SysFont(None, self.help_font_size)
            self.alert_font = pygame.font.SysFont(None, self.alert_font_size)
        except Exception as e:
            print(f"Error initializing font: {e}. Using default font.")
            self.ui_font = pygame.font.Font(None, self.ui_font_size)
            self.help_font = pygame.font.Font(None, self.help_font_size)
            self.alert_font = pygame.font.Font(None, self.alert_font_size)

        self.ui_line_height = self.ui_font.get_linesize()
        self.help_line_height = self.help_font.get_linesize()

        # Pre-render help text for performance (updated with UI toggle)
        self.help_text_lines = [
            "Controls: ↑/↓: Speed | Space: Reset Speed | S: Add Student | A: Add Adult | X: Add Shooter",
            "Toggles: V: Vision Cone | H: Hide/Show UI"
        ]
        self.rendered_help_lines = [
            self.help_font.render(line, True, self.COLORS["TEXT_COLOR"]) for line in self.help_text_lines
        ]

        # Alert system variables
        self.show_alert = False
        self.alert_message = ""
        self.alert_start_time = 0
        self.alert_duration = config.ALERT_DURATION
        self.last_has_shooter = False

    def _create_cached_background(self):
        """Create a cached background with static elements (walls and doors)."""
        self.background = pygame.Surface((self.screen_width, self.screen_height))
        self.background.fill(self.COLORS["WHITE"])

        # Draw walls
        for wall_rect in self.model.walls:
            scaled_rect = self._scale_rect(wall_rect)
            pygame.draw.rect(self.background, self.COLORS["BLACK"], scaled_rect)

        # Draw doors
        door_color = self.COLORS["BROWN"]
        for door_rect in self.model.doors:
            scaled_rect = self._scale_rect(door_rect)
            pygame.draw.rect(self.background, door_color, scaled_rect)

    def _scale_rect(self, rect):
        """Scale a rect from model coordinates to screen coordinates."""
        return pygame.Rect(
            int(rect.left * self.scale_factor),
            int(rect.top * self.scale_factor),
            max(1, int(rect.width * self.scale_factor + 0.5)), # Ensure width is at least 1
            max(1, int(rect.height * self.scale_factor + 0.5)) # Ensure height is at least 1
        )

    def _model_to_screen_pos(self, pos):
        """Convert model coordinates to screen coordinates."""
        return int(pos[0] * self.scale_factor), int(pos[1] * self.scale_factor)

    def show_shooter_alert(self):
        """Display an active shooter alert."""
        self.show_alert = True
        self.alert_message = "⚠️ ACTIVE SHOOTER ALERT ⚠️"
        self.alert_start_time = time.time()

    def check_shooter_status(self):
        """Check if shooter status has changed and show alert if needed."""
        current_shooter_status = self.model.has_active_shooter
        if current_shooter_status and not self.last_has_shooter:
            self.show_shooter_alert()
        self.last_has_shooter = current_shooter_status

    def visualize_vision_cone(self, vision_angle=config.VISION_CONE_ANGLE,
                              max_vision_distance=config.MAX_VISION_DISTANCE):
        """Visualize the vision cone for active shooters."""
        shooters = self.model.active_shooters
        if not shooters:
            return

        temp_surface = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)

        for shooter in shooters:
            shooter_pos = shooter.position
            screen_shooter_pos = self._model_to_screen_pos(shooter_pos)

            facing_angle = getattr(shooter, 'direction', 0)
            if hasattr(shooter, 'locked_target') and shooter.locked_target:
                target_pos = shooter.locked_target.position
                dx = target_pos[0] - shooter_pos[0]
                dy = target_pos[1] - shooter_pos[1]
                if dx != 0 or dy != 0:
                    facing_angle = math.atan2(dy, dx)
            elif hasattr(shooter, 'velocity'):
                vx, vy = shooter.velocity
                if vx != 0 or vy != 0:
                    facing_angle = math.atan2(vy, vx)

            vision_angle_rad = math.radians(vision_angle)
            start_angle = facing_angle - vision_angle_rad / 2
            end_angle = facing_angle + vision_angle_rad / 2

            num_rays = 20
            polygon_points = [screen_shooter_pos]
            scaled_max_dist = max_vision_distance

            for i in range(num_rays + 1):
                ray_angle = start_angle + (end_angle - start_angle) * i / num_rays
                hit_point = cast_ray(
                    shooter_pos, ray_angle, scaled_max_dist, self.model.vision_blocking_obstacles
                )
                screen_endpoint = self._model_to_screen_pos(hit_point)
                polygon_points.append(screen_endpoint)

            if len(polygon_points) > 2:
                pygame.draw.polygon(temp_surface, (255, 255, 0, 40), polygon_points)
                pygame.draw.polygon(temp_surface, (255, 255, 0, 90), polygon_points, 1)

        self.screen.blit(temp_surface, (0, 0))

    def draw_alert(self):
        """Draw alert message on screen with pulsing effect."""
        if not self.show_alert:
            return

        current_time = time.time()
        if current_time - self.alert_start_time > self.alert_duration:
            self.show_alert = False
            return

        text_surface = self.alert_font.render(self.alert_message, True, self.COLORS["WHITE"])
        text_rect = text_surface.get_rect()

        padding = 10
        alert_width = text_rect.width + 2 * padding
        alert_height = text_rect.height + 2 * padding
        alert_surface = pygame.Surface((alert_width, alert_height), pygame.SRCALPHA)

        elapsed = current_time - self.alert_start_time
        pulse_factor = 0.7 + 0.3 * math.sin(elapsed * 6)
        alpha = int(150 + 55 * pulse_factor)

        alert_rect = pygame.Rect(0, 0, alert_width, alert_height)
        pygame.draw.rect(alert_surface, (200, 0, 0, alpha), alert_rect, border_radius=8)
        pygame.draw.rect(alert_surface, (255, 255, 255, 200), alert_rect, width=1, border_radius=8)

        text_x = padding
        text_y = padding
        alert_surface.blit(text_surface, (text_x, text_y))

        alert_x = (self.screen_width - alert_width) // 2
        alert_y = 60
        self.screen.blit(alert_surface, (alert_x, alert_y))

    def draw_agents(self):
        """Draw all agents with appropriate radii and status indicators."""
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)

        for agent in self.model.schedule:
            if not hasattr(agent, 'position'): continue

            pos = agent.position
            screen_pos = self._model_to_screen_pos(pos)

            # Determine base radius based on agent type
            if agent.agent_type == "student":
                base_radius = config.STUDENT_RADIUS
            elif agent.agent_type == "adult":
                base_radius = config.ADULT_RADIUS
            else:
                base_radius = config.STUDENT_RADIUS # Default if type unknown

            radius = max(1, int(base_radius * self.scale_factor))

            # Determine agent color
            if getattr(agent, "is_shooter", False):
                 color = self.COLORS["GREEN"]
            elif agent.agent_type == "student":
                if getattr(agent, "has_weapon", False):
                    color = self.COLORS["ARMED_STUDENT"]
                elif getattr(agent, "in_emergency", False):
                    color = self.COLORS["FLEEING_STUDENT"]
                else:
                    color = self.COLORS["BLUE"]
            elif agent.agent_type == "adult":
                if getattr(agent, "has_weapon", False):
                    color = self.COLORS["ARMED_ADULT"]
                elif getattr(agent, "aware_of_shooter", False):
                    color = self.COLORS["AWARE_ADULT"]
                else:
                    color = self.COLORS["RED"]
            else:
                 color = self.COLORS["BLACK"] # Default fallback

            # Draw agent circle
            pygame.draw.circle(self.screen, color, screen_pos, radius)

            # Draw direction indicator if moving
            if hasattr(agent, "velocity"):
                vx, vy = agent.velocity
                speed_squared = vx * vx + vy * vy
                if speed_squared > 0.01:
                    speed = math.sqrt(speed_squared)
                    dir_len = radius * 0.8
                    end_pos = (
                        int(screen_pos[0] + (vx / speed) * dir_len),
                        int(screen_pos[1] + (vy / speed) * dir_len)
                    )
                    pygame.draw.line(self.screen, self.COLORS["BLACK"], screen_pos, end_pos, 1)

            # Draw scream radius for students in emergency
            if (config.ENABLE_STUDENT_SCREAMING and agent.agent_type == "student"
                    and getattr(agent, "in_emergency", False)):
                scream_radius = int(config.SCREAM_RADIUS * self.scale_factor)
                if scream_radius > 1:
                    scream_fill = self.COLORS["SCREAM_FILL"]
                    scream_outline = self.COLORS["SCREAM_OUTLINE"]
                    pygame.draw.circle(overlay, scream_fill, screen_pos, scream_radius)
                    pygame.draw.circle(overlay, scream_outline, screen_pos, scream_radius, 1)

        self.screen.blit(overlay, (0, 0))

    def draw_shots(self):
        """Draw active gunshots."""
        current_time = self.model.simulation_time
        shot_duration = config.SHOT_VISUALIZATION_DURATION

        valid_shots = [
            shot for shot in self.model.active_shots
            if current_time - shot['start_time'] < shot_duration
        ]

        shot_color = self.COLORS["SHOT"]
        for shot in valid_shots:
            start_screen = self._model_to_screen_pos(shot['start_pos'])
            end_screen = self._model_to_screen_pos(shot['end_pos'])
            pygame.draw.line(self.screen, shot_color, start_screen, end_screen, 1)

        if len(valid_shots) != len(self.model.active_shots):
            self.model.active_shots = valid_shots

    def draw_exits(self):
        """Draw exit areas."""
        exit_fill = self.COLORS["EXIT_FILL"]
        exit_border = self.COLORS["EXIT_BORDER"]

        for exit_rect in self.model.exits:
            scaled_rect = self._scale_rect(exit_rect)
            pygame.draw.rect(self.screen, exit_fill, scaled_rect)
            pygame.draw.rect(self.screen, exit_border, scaled_rect, 1)

    def draw_ui(self, simulation_time, sim_speed, fps, show_vision):
        """Draw user interface elements in compact panels."""
        # This function now assumes it's only called when show_ui is True.
        # The conditional check happens in render_frame.

        student_count = 0
        adult_count = 0
        for agent in self.model.schedule:
            if agent.agent_type == "student": student_count += 1
            elif agent.agent_type == "adult": adult_count += 1
        shooter_count = len(self.model.active_shooters)

        panel_color = self.COLORS["PANEL_BG"]
        text_color = self.COLORS["TEXT_COLOR"]
        padding = 10
        v_padding = 5

        # --- Top Info Panel ---
        panel_height = self.ui_line_height + v_padding * 2
        panel_surface = pygame.Surface((self.screen_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill(panel_color)

        time_str = f"Time: {simulation_time:.1f}s"
        speed_str = f"Speed: {sim_speed:.1f}x"
        agent_str = f"Agents: {student_count} S / {adult_count} A"
        shooter_str = f"Shooters: {shooter_count}"
        fps_str = f"FPS: {fps:.0f}"
        vision_str = f"Vision Cone [V]: {'ON' if show_vision else 'OFF'}"

        time_surf = self.ui_font.render(time_str, True, text_color)
        speed_surf = self.ui_font.render(speed_str, True, text_color)
        agent_surf = self.ui_font.render(agent_str, True, text_color)
        shooter_color = self.COLORS["ALERT"] if shooter_count > 0 else text_color
        shooter_surf = self.ui_font.render(shooter_str, True, shooter_color)
        fps_surf = self.ui_font.render(fps_str, True, text_color)
        vision_surf = self.ui_font.render(vision_str, True, text_color)

        x_pos = padding
        y_pos = v_padding

        panel_surface.blit(time_surf, (x_pos, y_pos))
        x_pos += time_surf.get_width() + padding * 2
        panel_surface.blit(speed_surf, (x_pos, y_pos))
        x_pos += speed_surf.get_width() + padding * 2
        panel_surface.blit(agent_surf, (x_pos, y_pos))
        x_pos += agent_surf.get_width() + padding * 2
        panel_surface.blit(shooter_surf, (x_pos, y_pos))

        vision_x = self.screen_width - vision_surf.get_width() - padding
        fps_x = vision_x - fps_surf.get_width() - padding * 2
        panel_surface.blit(fps_surf, (fps_x, y_pos))
        panel_surface.blit(vision_surf, (vision_x, y_pos))

        self.screen.blit(panel_surface, (0, 0))

        # --- Bottom Help Text Panel ---
        # Use the pre-rendered help lines from __init__
        help_panel_height = (len(self.rendered_help_lines) * self.help_line_height) + v_padding * 2
        help_panel_y = self.screen_height - help_panel_height
        help_panel_surface = pygame.Surface((self.screen_width, help_panel_height), pygame.SRCALPHA)
        help_panel_surface.fill(panel_color)

        help_y = v_padding
        for line_surf in self.rendered_help_lines:
            help_panel_surface.blit(line_surf, (padding, help_y))
            help_y += self.help_line_height

        self.screen.blit(help_panel_surface, (0, help_panel_y))


    def render_frame(self, simulation_time, sim_speed, fps=0, show_vision=False, show_ui=True):
        """Render a complete frame of the simulation."""
        # Draw cached background (walls, doors)
        self.screen.blit(self.background, (0, 0))

        # Check for shooter status change for alert
        self.check_shooter_status()

        # Draw dynamic elements
        self.draw_exits()
        self.draw_agents() # Handles different radii now
        self.draw_shots()

        # Draw visualizations (if enabled)
        if show_vision:
            self.visualize_vision_cone()

        # Draw UI elements only if enabled
        if show_ui:
            self.draw_ui(simulation_time, sim_speed, fps, show_vision)

        # Draw alert message if active (always on top if active)
        self.draw_alert()

        # Update the full display
        pygame.display.flip()

    def close(self):
        """Clean up Pygame resources."""
        pygame.font.quit()
        pygame.display.quit()
