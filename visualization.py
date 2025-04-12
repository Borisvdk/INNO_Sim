import pygame
import math
import time
from utilities import has_line_of_sight, cast_ray
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
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("School Safety Simulation")

        # Use colors from config
        self.COLORS = config.COLORS
        if "BROWN" not in self.COLORS:
            self.COLORS["BROWN"] = (139, 69, 19)

        # Create cached background with walls and doors
        self._create_cached_background()

        # Prepare fonts for UI elements
        self.font = pygame.font.SysFont(None, 24)
        self.alert_font = pygame.font.SysFont(None, 36)

        # Pre-render help text for performance
        self.help_text = self.font.render(
            "↑/↓: Speed up/down | Space: Reset speed | S: Add students | A: Add adults | X: Add shooter",
            True, self.COLORS["BLACK"]
        )
        self.viz_help_text = self.font.render(
            "V: Toggle Vision Cone | B: Toggle Safe Areas",
            True, self.COLORS["BLACK"]
        )

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
        door_color = self.COLORS.get("BROWN", (139, 69, 19))
        for door_rect in self.model.doors:
            scaled_rect = self._scale_rect(door_rect)
            pygame.draw.rect(self.background, door_color, scaled_rect)

    def _scale_rect(self, rect):
        """Scale a rect from model coordinates to screen coordinates."""
        return pygame.Rect(
            int(rect.left * self.scale_factor),
            int(rect.top * self.scale_factor),
            int(rect.width * self.scale_factor + 0.5),
            int(rect.height * self.scale_factor + 0.5)
        )

    def _model_to_screen_pos(self, pos):
        """Convert model coordinates to screen coordinates."""
        return (int(pos[0] * self.scale_factor), int(pos[1] * self.scale_factor))

    def show_shooter_alert(self):
        """Display an active shooter alert."""
        self.show_alert = True
        self.alert_message = "⚠️ ACTIVE SHOOTER ALERT ⚠️"
        self.alert_start_time = time.time()

    def check_shooter_status(self):
        """Check if shooter status has changed and show alert if needed."""
        if self.model.has_active_shooter and not self.last_has_shooter:
            self.show_shooter_alert()
        self.last_has_shooter = self.model.has_active_shooter

    def visualize_vision_cone(self, vision_angle=config.VISION_CONE_ANGLE,
                              max_vision_distance=config.MAX_VISION_DISTANCE):
        """Visualize the vision cone for active shooters."""
        # Find shooters
        shooters = [agent for agent in self.model.schedule if getattr(agent, 'is_shooter', False)]
        if not shooters:
            return

        # Create a transparent surface for visualization
        temp_surface = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)

        # Draw vision cone for each shooter
        for shooter in shooters:
            shooter_pos = shooter.position
            screen_shooter_pos = self._model_to_screen_pos(shooter_pos)

            # Determine facing direction
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

            # Calculate vision cone angles
            vision_angle_rad = math.radians(vision_angle)
            start_angle = facing_angle - vision_angle_rad / 2
            end_angle = facing_angle + vision_angle_rad / 2

            # Create polygon points for vision cone
            num_rays = 30
            polygon_points = [screen_shooter_pos]

            for i in range(num_rays):
                ray_angle = start_angle + (end_angle - start_angle) * i / (num_rays - 1)
                ray_endpoint = cast_ray(
                    shooter_pos, ray_angle, max_vision_distance, self.model.vision_blocking_obstacles
                )
                screen_endpoint = self._model_to_screen_pos(ray_endpoint)
                polygon_points.append(screen_endpoint)

            # Draw vision cone
            if len(polygon_points) > 2:
                pygame.draw.polygon(temp_surface, (255, 255, 0, 60), polygon_points)
                pygame.draw.polygon(temp_surface, (255, 255, 0, 120), polygon_points, 1)

            # Draw direction indicator
            dir_len = 20 * self.scale_factor
            dir_endpoint = (
                screen_shooter_pos[0] + math.cos(facing_angle) * dir_len,
                screen_shooter_pos[1] + math.sin(facing_angle) * dir_len
            )
            pygame.draw.line(temp_surface, (255, 255, 0, 200), screen_shooter_pos, dir_endpoint, 2)

            # Draw line-of-sight to visible agents
            for agent in self.model.schedule:
                if agent == shooter:
                    continue

                agent_pos = agent.position
                screen_agent_pos = self._model_to_screen_pos(agent_pos)

                has_sight = has_line_of_sight(shooter_pos, agent_pos, self.model.vision_blocking_obstacles)
                if has_sight:
                    pygame.draw.line(temp_surface, (0, 255, 0, 180), screen_shooter_pos, screen_agent_pos, 2)

                    # Highlight locked target
                    if hasattr(shooter, 'locked_target') and agent == shooter.locked_target:
                        pygame.draw.circle(temp_surface, (255, 0, 0, 180), screen_agent_pos,
                                           int(8 * self.scale_factor), 2)

        self.screen.blit(temp_surface, (0, 0))

    def visualize_safe_spawn_areas(self):
        """Visualize areas where agents can safely spawn."""
        temp_surface = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        grid_step = 20  # Larger step for better performance

        for x in range(0, self.model.width, grid_step):
            for y in range(0, self.model.height, grid_step):
                # Check if point is in a wall
                is_in_wall = any(wall_rect.collidepoint(x, y) for wall_rect in self.model.walls)

                screen_pos = self._model_to_screen_pos((x, y))
                color = (255, 0, 0, 100) if is_in_wall else (0, 255, 0, 40)
                pygame.draw.circle(temp_surface, color, screen_pos, 3)

        self.screen.blit(temp_surface, (0, 0))

    def draw_alert(self):
        """Draw alert message on screen with pulsing effect."""
        if not self.show_alert:
            return

        current_time = time.time()
        if current_time - self.alert_start_time > self.alert_duration:
            self.show_alert = False
            return

        # Create alert text
        text_surface = self.alert_font.render(self.alert_message, True, self.COLORS["WHITE"])
        text_rect = text_surface.get_rect()

        # Create alert box
        alert_width = text_rect.width + 40
        alert_height = text_rect.height + 20
        alert_surface = pygame.Surface((alert_width, alert_height), pygame.SRCALPHA)

        # Pulse effect
        elapsed = current_time - self.alert_start_time
        pulse_factor = 0.5 + 0.5 * math.sin(elapsed * 10)
        alpha = int(180 + 75 * pulse_factor)

        # Draw alert box with border
        alert_rect = pygame.Rect(0, 0, alert_width, alert_height)
        pygame.draw.rect(alert_surface, (255, 0, 0, alpha), alert_rect, border_radius=10)
        pygame.draw.rect(alert_surface, (255, 255, 255, 255), alert_rect, width=2, border_radius=10)

        # Position and add text
        text_x = (alert_width - text_rect.width) // 2
        text_y = (alert_height - text_rect.height) // 2
        alert_surface.blit(text_surface, (text_x, text_y))

        # Position and draw alert
        alert_x = (self.screen_width - alert_width) // 2
        alert_y = 100
        self.screen.blit(alert_surface, (alert_x, alert_y))

    def draw_agents(self):
        """Draw all agents and their status indicators."""
        # Create overlay for transparent elements
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)

        # Prepare agent drawing
        for agent in self.model.schedule:
            pos = agent.position
            screen_pos = self._model_to_screen_pos(pos)
            radius = max(1, int(agent.radius * self.scale_factor))

            # Determine agent color based on type and status
            if agent.agent_type == "student":
                if getattr(agent, "is_shooter", False):
                    color = self.COLORS["GREEN"]
                elif getattr(agent, "has_weapon", False):
                    color = self.COLORS["ARMED_STUDENT"]
                elif getattr(agent, "in_emergency", False):
                    color = (0, 100, 255)  # Darker blue for fleeing
                else:
                    color = self.COLORS["BLUE"]
            else:  # adult
                if getattr(agent, "has_weapon", False):
                    color = (255, 255, 0)  # Yellow for armed
                elif getattr(agent, "aware_of_shooter", False):
                    color = (255, 100, 0)  # Orange for aware
                else:
                    color = self.COLORS["RED"]

            # Draw agent circle
            pygame.draw.circle(self.screen, color, screen_pos, radius)

            # Draw direction indicator if moving
            if hasattr(agent, "velocity"):
                vx, vy = agent.velocity
                speed_squared = vx * vx + vy * vy
                if speed_squared > 0.01:
                    speed = math.sqrt(speed_squared)
                    dir_len = radius + 2
                    dir_x = vx / speed * dir_len
                    dir_y = vy / speed * dir_len
                    end_pos = (int(screen_pos[0] + dir_x), int(screen_pos[1] + dir_y))
                    pygame.draw.line(self.screen, self.COLORS["BLACK"], screen_pos, end_pos, 1)

            # Draw scream radius for students in emergency
            if (config.ENABLE_STUDENT_SCREAMING and agent.agent_type == "student"
                    and getattr(agent, "in_emergency", False)):
                scream_radius = int(config.SCREAM_RADIUS * self.scale_factor)
                if scream_radius > 0:
                    pygame.draw.circle(overlay, self.COLORS["SCREAM_FILL"], screen_pos, scream_radius)
                    pygame.draw.circle(overlay, self.COLORS["SCREAM_OUTLINE"], screen_pos, scream_radius, 1)

        # Draw overlay
        self.screen.blit(overlay, (0, 0))

    def draw_shots(self):
        """Draw active gunshots."""
        current_time = self.model.simulation_time
        shot_duration = config.SHOT_VISUALIZATION_DURATION
        shots_to_remove = []

        for i, shot in enumerate(self.model.active_shots):
            if current_time - shot['start_time'] < shot_duration:
                start_screen = self._model_to_screen_pos(shot['start_pos'])
                end_screen = self._model_to_screen_pos(shot['end_pos'])
                pygame.draw.line(self.screen, (255, 0, 0), start_screen, end_screen, 2)
            else:
                shots_to_remove.append(i)

        # Remove expired shots
        for i in sorted(shots_to_remove, reverse=True):
            if i < len(self.model.active_shots):
                self.model.active_shots.pop(i)

    def draw_exits(self):
        """Draw exit areas."""
        exit_color = (0, 255, 0, 150)
        exit_border_color = (0, 100, 0)

        for exit_rect in self.model.exits:
            scaled_rect = self._scale_rect(exit_rect)
            pygame.draw.rect(self.screen, exit_color, scaled_rect)
            pygame.draw.rect(self.screen, exit_border_color, scaled_rect, 1)

    def draw_ui(self, simulation_time, sim_speed, fps, show_vision, show_safe_areas):
        """Draw user interface elements."""
        # Count agents by type
        student_count = sum(1 for agent in self.model.schedule if agent.agent_type == "student")
        adult_count = sum(1 for agent in self.model.schedule if agent.agent_type == "adult")
        shooter_count = len(self.model.active_shooters)

        # Prepare UI text
        time_text = self.font.render(f"Sim Time: {simulation_time:.1f}s", True, self.COLORS["BLACK"])
        speed_text = self.font.render(f"Speed: {sim_speed:.1f}x", True, self.COLORS["BLACK"])
        count_text = self.font.render(f"Students: {student_count}, Adults: {adult_count}", True, self.COLORS["BLACK"])
        fps_text = self.font.render(f"FPS: {fps:.1f}", True, self.COLORS["BLACK"])

        shooter_color = self.COLORS["ALERT"] if shooter_count > 0 else self.COLORS["BLACK"]
        shooter_text = self.font.render(f"Active Shooters: {shooter_count}", True, shooter_color)

        vision_status = "ON" if show_vision else "OFF"
        safe_status = "ON" if show_safe_areas else "OFF"
        viz_status_text = self.font.render(
            f"Vision Cone: {vision_status} | Safe Areas: {safe_status}",
            True, self.COLORS["BLACK"]
        )

        # Draw UI elements in top-left
        text_y = 10
        line_height = 30
        self.screen.blit(time_text, (10, text_y))
        text_y += line_height
        self.screen.blit(speed_text, (10, text_y))
        text_y += line_height
        self.screen.blit(count_text, (10, text_y))
        text_y += line_height
        self.screen.blit(shooter_text, (10, text_y))
        text_y += line_height
        self.screen.blit(fps_text, (10, text_y))
        text_y += line_height
        self.screen.blit(viz_status_text, (10, text_y))

        # Draw help text at bottom
        self.screen.blit(self.help_text, (10, self.screen_height - 50))
        self.screen.blit(self.viz_help_text, (10, self.screen_height - 25))

    def render_frame(self, simulation_time, sim_speed, fps=0, show_vision=False, show_safe_areas=False):
        """Render a complete frame of the simulation."""
        # Draw background with walls and doors
        self.screen.blit(self.background, (0, 0))

        # Check for shooter status change
        self.check_shooter_status()

        # Draw safe spawn areas if enabled
        if show_safe_areas:
            self.visualize_safe_spawn_areas()

        # Draw exits
        self.draw_exits()

        # Draw all agents
        self.draw_agents()

        # Draw vision cone if enabled
        if show_vision:
            self.visualize_vision_cone()

        # Draw active shots
        self.draw_shots()

        # Draw UI elements
        self.draw_ui(simulation_time, sim_speed, fps, show_vision, show_safe_areas)

        # Draw alert if active
        self.draw_alert()

        # Update display
        pygame.display.flip()