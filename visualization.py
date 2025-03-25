import pygame
import math
import time
from utilities import has_line_of_sight, cast_ray, distance_squared
import config


class Visualizer:
    """Class to handle all visualization aspects of the simulation."""

    def __init__(self, model, screen_width=config.SCREEN_WIDTH, screen_height=config.SCREEN_HEIGHT):
        self.model = model
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.scale_factor = min(screen_width / model.width, screen_height / model.height)

        # Initialize Pygame components
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("School Safety Simulation")

        # Use colors from config
        self.COLORS = config.COLORS

        # Create a cached background with walls
        self.background = pygame.Surface((screen_width, screen_height))
        self.background.fill(self.COLORS["WHITE"])

        # Draw walls on background
        for wall in model.walls:
            x_min, y_min, x_max, y_max = wall
            pygame.draw.rect(
                self.background,
                self.COLORS["BLACK"],
                pygame.Rect(
                    x_min * self.scale_factor,
                    y_min * self.scale_factor,
                    (x_max - x_min) * self.scale_factor,
                    (y_max - y_min) * self.scale_factor
                )
            )

        # Create font for UI text
        self.font = pygame.font.SysFont(None, 24)
        self.alert_font = pygame.font.SysFont(None, 36)

        # Pre-render help text, now including the X key for manual shooter
        self.help_text = self.font.render(
            "↑/↓: Speed up/down | Space: Reset speed | S: Add students | A: Add adults | E: Emergency evacuation | X: Add shooter",
            True, self.COLORS["BLACK"]
        )

        # Add visualization controls description
        self.viz_help_text = self.font.render(
            "V: Toggle Line of Sight | B: Toggle Safe Areas",
            True, self.COLORS["BLACK"]
        )

        # Alert system variables
        self.show_alert = False
        self.alert_message = ""
        self.alert_start_time = 0
        self.alert_duration = config.ALERT_DURATION  # seconds
        self.last_has_shooter = False

    def check_shooter_status(self):
        """Check if shooter status has changed and show alert if needed"""
        # Check if we now have a shooter but didn't before
        if self.model.has_active_shooter and not self.last_has_shooter:
            self.show_shooter_alert()

        # Update last shooter status
        self.last_has_shooter = self.model.has_active_shooter

    def show_shooter_alert(self):
        """Display an active shooter alert"""
        self.show_alert = True
        self.alert_message = "⚠️ ACTIVE SHOOTER ALERT ⚠️"
        self.alert_start_time = time.time()

    def visualize_line_of_sight(self, shooter_agent=None):
        """Visualize the line of sight for the shooter agent."""
        # Find a shooter if none provided
        if shooter_agent is None:
            for agent in self.model.schedule:
                if hasattr(agent, 'is_shooter') and agent.is_shooter:
                    shooter_agent = agent
                    break

            if shooter_agent is None:
                return  # No shooter found

        # Get shooter position
        shooter_x, shooter_y = shooter_agent.position
        screen_shooter_x = int(shooter_x * self.scale_factor)
        screen_shooter_y = int(shooter_y * self.scale_factor)

        # Create a semi-transparent surface for lines
        temp_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)

        # Draw a larger circle for the shooter
        pygame.draw.circle(
            temp_surface,
            (255, 0, 0, 180),  # Semi-transparent red
            (screen_shooter_x, screen_shooter_y),
            int(12 * self.scale_factor)
        )

        # Check if the shooter has a locked target
        if hasattr(shooter_agent, 'locked_target') and shooter_agent.locked_target is not None:
            target = shooter_agent.locked_target
            target_x, target_y = target.position
            screen_target_x = int(target_x * self.scale_factor)
            screen_target_y = int(target_y * self.scale_factor)

            # Draw a line to the target
            pygame.draw.line(
                temp_surface,
                (255, 0, 0, 220),  # More opaque red for locked target
                (screen_shooter_x, screen_shooter_y),
                (screen_target_x, screen_target_y),
                3  # Thicker line for locked target
            )

            # Draw a target circle
            pygame.draw.circle(
                temp_surface,
                (255, 0, 0, 180),
                (screen_target_x, screen_target_y),
                int(8 * self.scale_factor),
                2  # Outline only
            )

        # Visualize line of sight to all other agents
        for agent in self.model.schedule:
            if agent == shooter_agent or (
                    hasattr(shooter_agent, 'locked_target') and agent == shooter_agent.locked_target):
                continue  # Skip shooter and locked target (already visualized)

            # Get agent position
            agent_x, agent_y = agent.position
            screen_agent_x = int(agent_x * self.scale_factor)
            screen_agent_y = int(agent_y * self.scale_factor)

            # Check line of sight
            has_sight = has_line_of_sight(shooter_agent.position, agent.position, self.model.walls)

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
        self.screen.blit(temp_surface, (0, 0))

    def visualize_vision_cone(self, shooter_agent=None, vision_angle=config.VISION_CONE_ANGLE,
                              max_vision_distance=config.MAX_VISION_DISTANCE):
        """Visualize the vision cone for the shooter agent, properly blocked by walls."""
        # Find a shooter if none provided
        if shooter_agent is None:
            for agent in self.model.schedule:
                if hasattr(agent, 'is_shooter') and agent.is_shooter:
                    shooter_agent = agent
                    break

            if shooter_agent is None:
                return  # No shooter found

        # Get shooter position
        shooter_x, shooter_y = shooter_agent.position
        screen_shooter_x = int(shooter_x * self.scale_factor)
        screen_shooter_y = int(shooter_y * self.scale_factor)

        # Create a semi-transparent surface for the vision cone
        temp_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)

        # Determine the facing direction
        facing_angle = 0  # Default direction

        # First, check if the shooter is currently targeting someone
        current_target = None
        if hasattr(shooter_agent, 'locked_target') and shooter_agent.locked_target is not None:
            current_target = shooter_agent.locked_target
        else:
            current_target = self.find_shooter_target(shooter_agent)

        if current_target:
            # Calculate direction toward target
            target_x, target_y = current_target.position
            dx = target_x - shooter_x
            dy = target_y - shooter_y
            facing_angle = math.atan2(dy, dx)
        elif hasattr(shooter_agent, 'velocity') and (shooter_agent.velocity[0] != 0 or shooter_agent.velocity[1] != 0):
            # Use movement direction if not targeting and moving
            vx, vy = shooter_agent.velocity
            facing_angle = math.atan2(vy, vx)
        else:
            # Use stored direction if available
            facing_angle = getattr(shooter_agent, 'direction', 0)

        # Convert vision angle from degrees to radians
        vision_angle_rad = math.radians(vision_angle)

        # Calculate the start and end angles for the vision cone
        start_angle = facing_angle - vision_angle_rad / 2
        end_angle = facing_angle + vision_angle_rad / 2

        # Number of rays to cast
        num_rays = 60

        # Calculate all the points for the vision cone polygon
        polygon_points = [(screen_shooter_x, screen_shooter_y)]  # Start with shooter position

        # Cast rays at regular angular intervals
        for i in range(num_rays):
            ray_angle = start_angle + (end_angle - start_angle) * i / (num_rays - 1)

            # Cast a ray in this direction
            ray_endpoint = cast_ray(
                shooter_agent.position,
                ray_angle,
                max_vision_distance,
                self.model.walls
            )

            # Convert to screen coordinates
            screen_endpoint = (
                int(ray_endpoint[0] * self.scale_factor),
                int(ray_endpoint[1] * self.scale_factor)
            )
            polygon_points.append(screen_endpoint)

        # Draw the vision cone as a filled polygon
        if len(polygon_points) > 2:
            pygame.draw.polygon(temp_surface, (255, 255, 0, 60), polygon_points)  # Semi-transparent yellow

            # Draw the outline of the vision cone
            pygame.draw.polygon(temp_surface, (255, 255, 0, 120), polygon_points, 1)  # Slightly more opaque outline

        # Draw a line showing the facing direction
        dir_endpoint = (
            screen_shooter_x + math.cos(facing_angle) * 30,
            screen_shooter_y + math.sin(facing_angle) * 30
        )
        pygame.draw.line(temp_surface, (255, 255, 0, 200),
                         (screen_shooter_x, screen_shooter_y), dir_endpoint, 2)

        # If we have a target, highlight it
        if current_target:
            target_x, target_y = current_target.position
            screen_target_x = int(target_x * self.scale_factor)
            screen_target_y = int(target_y * self.scale_factor)

            # Draw a line to the target
            pygame.draw.line(temp_surface, (255, 0, 0, 180),
                             (screen_shooter_x, screen_shooter_y),
                             (screen_target_x, screen_target_y), 1)

            # Draw a circle around the target
            pygame.draw.circle(temp_surface, (255, 0, 0, 180),
                               (screen_target_x, screen_target_y),
                               int(6 * self.scale_factor), 1)

        # Blit the temporary surface to the screen
        self.screen.blit(temp_surface, (0, 0))

    def find_shooter_target(self, shooter_agent):
        """Find the current target of the shooter based on proximity and line of sight."""
        # If the shooter has a locked target attribute, use that
        if hasattr(shooter_agent, 'locked_target') and shooter_agent.locked_target is not None:
            return shooter_agent.locked_target

        # If the shooter is not moving (velocity near zero), it might be aiming
        if hasattr(shooter_agent, 'velocity'):
            vx, vy = shooter_agent.velocity
            speed_squared = vx * vx + vy * vy

            if speed_squared < 0.1:  # Almost stationary
                # Find visible target agents in range
                search_radius = getattr(shooter_agent, 'shooting_range', 150) * 1.5
                nearby_agents = self.model.spatial_grid.get_nearby_agents(shooter_agent.position, search_radius)

                # Filter for valid targets with line of sight
                visible_targets = []
                for agent in nearby_agents:
                    if agent != shooter_agent and agent.agent_type in ["student", "adult"]:
                        if has_line_of_sight(shooter_agent.position, agent.position, self.model.walls):
                            visible_targets.append((agent, distance_squared(shooter_agent.position, agent.position)))

                # Sort targets by distance
                if visible_targets:
                    visible_targets.sort(key=lambda x: x[1])  # Sort by distance
                    return visible_targets[0][0]  # Return the closest visible target

        return None

    def visualize_safe_spawn_areas(self):
        """Visualize the areas where agents can safely spawn (not in walls)."""
        # Create a temporary surface for drawing with alpha
        temp_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)

        # Sample a grid of points and check if they're in a wall
        grid_step = 10  # Controls the density of sampling points

        for x in range(0, self.model.width, grid_step):
            for y in range(0, self.model.height, grid_step):
                # Check if position is inside any wall
                is_in_wall = False
                for wall in self.model.walls:
                    wall_x1, wall_y1, wall_x2, wall_y2 = wall
                    if (wall_x1 <= x <= wall_x2 and wall_y1 <= y <= wall_y2):
                        is_in_wall = True
                        break

                # Convert to screen coordinates
                screen_x = int(x * self.scale_factor)
                screen_y = int(y * self.scale_factor)

                # Draw a dot
                color = (255, 0, 0, 100) if is_in_wall else (0, 255, 0, 40)  # Red for unsafe, green for safe
                radius = 3
                pygame.draw.circle(temp_surface, color, (screen_x, screen_y), radius)

        # Draw the surface
        self.screen.blit(temp_surface, (0, 0))

    def draw_alert(self):
        """Draw an alert message on the screen"""
        if not self.show_alert:
            return

        # Check if alert should still be shown
        current_time = time.time()
        if current_time - self.alert_start_time > self.alert_duration:
            self.show_alert = False
            return

        # Calculate alert box size and position
        text_surface = self.alert_font.render(self.alert_message, True, self.COLORS["WHITE"])
        text_rect = text_surface.get_rect()

        alert_width = text_rect.width + 40
        alert_height = text_rect.height + 20
        alert_x = (self.screen_width - alert_width) // 2
        alert_y = 100

        # Create alert surface with transparency
        alert_surface = pygame.Surface((alert_width, alert_height), pygame.SRCALPHA)

        # Calculate pulsing effect - alpha varies between 180 and 255
        elapsed = current_time - self.alert_start_time
        pulse_factor = 0.5 + 0.5 * math.sin(elapsed * 10)  # Pulsing frequency
        alpha = int(180 + 75 * pulse_factor)

        # Draw alert background with pulsing effect
        pygame.draw.rect(
            alert_surface,
            (255, 0, 0, alpha),  # Red with pulsing alpha
            pygame.Rect(0, 0, alert_width, alert_height),
            border_radius=10
        )

        # Draw text
        text_x = (alert_width - text_rect.width) // 2
        text_y = (alert_height - text_rect.height) // 2
        alert_surface.blit(text_surface, (text_x, text_y))

        # Draw border
        pygame.draw.rect(
            alert_surface,
            (255, 255, 255, 255),  # White border
            pygame.Rect(0, 0, alert_width, alert_height),
            width=2,
            border_radius=10
        )

        # Draw the alert
        self.screen.blit(alert_surface, (alert_x, alert_y))

    def render_frame(self, simulation_time, sim_speed, fps=0, show_line_of_sight=False, show_safe_areas=False):
        """Render a complete frame of the simulation."""
        # Draw background (with walls)
        self.screen.blit(self.background, (0, 0))

        # Check for shooter status changes
        self.check_shooter_status()

        # Visualize safe areas if enabled
        if show_safe_areas:
            self.visualize_safe_spawn_areas()

        # Pre-calculate draw lists for batch rendering
        circles_to_draw = []
        lines_to_draw = []

        for agent in self.model.schedule:
            x, y = agent.position
            screen_x = int(x * self.scale_factor)
            screen_y = int(y * self.scale_factor)
            scaled_radius = int(agent.radius * self.scale_factor)

            # Determine color
            if agent.agent_type == "student":
                if getattr(agent, "is_shooter", False):
                    color = self.COLORS["GREEN"]
                elif getattr(agent, "has_weapon", False):
                    color = self.COLORS["ARMED_STUDENT"]
                else:
                    color = self.COLORS["BLUE"]
            else:  # adult
                color = self.COLORS["ARMED_ADULT"] if getattr(agent, "has_weapon", False) else self.COLORS["RED"]

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
                        (self.COLORS["BLACK"], (screen_x, screen_y),
                         (screen_x + direction_x, screen_y + direction_y), 1)
                    )

        # Draw all circles in batch
        for color, pos, radius in circles_to_draw:
            pygame.draw.circle(self.screen, color, pos, radius)

        # Draw all lines in batch
        for color, start, end, width in lines_to_draw:
            pygame.draw.line(self.screen, color, start, end, width)

        # Visualize line of sight if enabled
        if show_line_of_sight:
            self.visualize_vision_cone()

        # Process and draw active shots efficiently
        shot_duration = config.SHOT_VISUALIZATION_DURATION
        shots_to_remove = []
        current_sim_time = self.model.simulation_time

        for i, shot in enumerate(self.model.active_shots):
            if current_sim_time - shot['start_time'] < shot_duration:
                # Scale shot coordinates
                start_x, start_y = shot['start_pos']
                end_x, end_y = shot['end_pos']
                screen_start = (int(start_x * self.scale_factor), int(start_y * self.scale_factor))
                screen_end = (int(end_x * self.scale_factor), int(end_y * self.scale_factor))
                pygame.draw.line(self.screen, (255, 0, 0), screen_start, screen_end, 2)
            else:
                shots_to_remove.append(i)

        # Remove expired shots - start from highest index to avoid shifting issues
        for i in sorted(shots_to_remove, reverse=True):
            if i < len(self.model.active_shots):
                self.model.active_shots.pop(i)

        # Count agents for display
        student_count = sum(1 for agent in self.model.schedule if agent.agent_type == "student")
        adult_count = sum(1 for agent in self.model.schedule if agent.agent_type == "adult")
        shooter_count = sum(1 for agent in self.model.schedule if hasattr(agent, "is_shooter") and agent.is_shooter)

        # Render dynamic UI text
        time_text = self.font.render(f"Sim Time: {simulation_time:.1f}s", True, self.COLORS["BLACK"])
        speed_text = self.font.render(f"Speed: {sim_speed:.1f}x", True, self.COLORS["BLACK"])
        count_text = self.font.render(f"Students: {student_count}, Adults: {adult_count}", True, self.COLORS["BLACK"])
        fps_text = self.font.render(f"FPS: {fps:.1f}", True, self.COLORS["BLACK"])

        # Show shooter count
        shooter_text_color = self.COLORS["ALERT"] if shooter_count > 0 else self.COLORS["BLACK"]
        shooter_text = self.font.render(f"Active Shooters: {shooter_count}", True, shooter_text_color)

        # Visualization status text
        los_status = "ON" if show_line_of_sight else "OFF"
        safe_status = "ON" if show_safe_areas else "OFF"
        viz_status_text = self.font.render(
            f"Line of Sight: {los_status} | Safe Areas: {safe_status}",
            True, self.COLORS["BLACK"]
        )

        # Draw UI text
        self.screen.blit(time_text, (10, 10))
        self.screen.blit(speed_text, (10, 40))
        self.screen.blit(count_text, (10, 70))
        self.screen.blit(shooter_text, (10, 100))
        self.screen.blit(fps_text, (10, 130))
        self.screen.blit(viz_status_text, (10, 160))
        self.screen.blit(self.help_text, (10, self.screen_height - 50))
        self.screen.blit(self.viz_help_text, (10, self.screen_height - 25))

        # Draw alert if active
        self.draw_alert()

        # Update display
        pygame.display.flip()