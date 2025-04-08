# --- START OF FILE visualization.py ---

import pygame
import math
import time
from utilities import has_line_of_sight, cast_ray, distance_squared # Ensure utilities uses Rects correctly
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

        # Use colors from config, and add door color if not present
        self.COLORS = config.COLORS
        if "BROWN" not in self.COLORS: # Add a default door color if needed
             self.COLORS["BROWN"] = (139, 69, 19) # Saddle Brown

        # Create a cached background with walls and doors
        self.background = pygame.Surface((screen_width, screen_height))
        self.background.fill(self.COLORS["WHITE"])

        # Draw walls (which are now Rects) on background
        for wall_rect in model.walls:
             scaled_rect = pygame.Rect(
                 int(wall_rect.left * self.scale_factor),
                 int(wall_rect.top * self.scale_factor),
                 int(wall_rect.width * self.scale_factor + 0.5), # Add 0.5 for rounding
                 int(wall_rect.height * self.scale_factor + 0.5)
             )
             pygame.draw.rect(self.background, self.COLORS["BLACK"], scaled_rect)

        # Draw DOORS on background
        door_color_bg = self.COLORS.get("BROWN", (139, 69, 19)) # Use config or default brown
        for door_rect in model.doors:
             scaled_rect = pygame.Rect(
                 int(door_rect.left * self.scale_factor),
                 int(door_rect.top * self.scale_factor),
                 int(door_rect.width * self.scale_factor + 0.5),
                 int(door_rect.height * self.scale_factor + 0.5)
             )
             pygame.draw.rect(self.background, door_color_bg, scaled_rect)

        # Create font for UI text
        self.font = pygame.font.SysFont(None, 24)
        self.alert_font = pygame.font.SysFont(None, 36)

        # Pre-render help text
        self.help_text = self.font.render(
            "↑/↓: Speed up/down | Space: Reset speed | S: Add students | A: Add adults | E: Emergency evacuation | X: Add shooter",
            True, self.COLORS["BLACK"]
        )
        self.viz_help_text = self.font.render(
            "V: Toggle Vision Cone | B: Toggle Safe Areas", # Updated V description
            True, self.COLORS["BLACK"]
        )

        # Alert system variables
        self.show_alert = False
        self.alert_message = ""
        self.alert_start_time = 0
        self.alert_duration = config.ALERT_DURATION
        self.last_has_shooter = False

    def check_shooter_status(self):
        """Check if shooter status has changed and show alert if needed"""
        if self.model.has_active_shooter and not self.last_has_shooter:
            self.show_shooter_alert()
        self.last_has_shooter = self.model.has_active_shooter

    def show_shooter_alert(self):
        """Display an active shooter alert"""
        self.show_alert = True
        self.alert_message = "⚠️ ACTIVE SHOOTER ALERT ⚠️"
        self.alert_start_time = time.time()

    def visualize_line_of_sight(self, shooter_agent=None):
        """Visualize the line of sight from the shooter to all other agents."""
        # Find a shooter if none provided
        if shooter_agent is None:
            shooters = [agent for agent in self.model.schedule if getattr(agent, 'is_shooter', False)]
            if not shooters: return
            shooter_agent = shooters[0] # Visualize first shooter found

        # Get shooter position
        shooter_x, shooter_y = shooter_agent.position
        screen_shooter_x = int(shooter_x * self.scale_factor)
        screen_shooter_y = int(shooter_y * self.scale_factor)

        # Use the combined list of visual obstacles
        all_obstacles = self.model.vision_blocking_obstacles

        # Create a semi-transparent surface for lines
        temp_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)

        # Draw a larger circle for the shooter
        pygame.draw.circle(temp_surface, (255, 0, 0, 180), (screen_shooter_x, screen_shooter_y), int(12 * self.scale_factor))

        # Visualize line of sight to all other agents
        for agent in self.model.schedule:
            if agent == shooter_agent: continue

            agent_x, agent_y = agent.position
            screen_agent_x = int(agent_x * self.scale_factor)
            screen_agent_y = int(agent_y * self.scale_factor)

            # Check line of sight using ALL obstacles
            has_sight = has_line_of_sight(shooter_agent.position, agent.position, all_obstacles)

            # Draw line with appropriate color
            line_color = (0, 255, 0, 180) if has_sight else (255, 0, 0, 64) # Green if visible, transparent red if not
            line_width = 2 if has_sight else 1
            pygame.draw.line(temp_surface, line_color, (screen_shooter_x, screen_shooter_y), (screen_agent_x, screen_agent_y), line_width)

            # Highlight locked target (if different from LoS check)
            if hasattr(shooter_agent, 'locked_target') and agent == shooter_agent.locked_target:
                 pygame.draw.circle(temp_surface, (255, 0, 0, 180), (screen_agent_x, screen_agent_y), int(8 * self.scale_factor), 2) # Target circle

        self.screen.blit(temp_surface, (0, 0))


    def visualize_vision_cone(self, shooter_agent=None, vision_angle=config.VISION_CONE_ANGLE,
                              max_vision_distance=config.MAX_VISION_DISTANCE):
        """Visualize the vision cone for the shooter agent, properly blocked by walls and doors."""
        # Find a shooter if none provided
        if shooter_agent is None:
            shooters = [agent for agent in self.model.schedule if getattr(agent, 'is_shooter', False)]
            if not shooters: return
            shooter_agent = shooters[0] # Visualize first shooter found

        shooter_x, shooter_y = shooter_agent.position
        screen_shooter_x = int(shooter_x * self.scale_factor)
        screen_shooter_y = int(shooter_y * self.scale_factor)

        # Use the combined list of visual obstacles
        all_obstacles = self.model.vision_blocking_obstacles

        temp_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)

        # Determine the facing direction (same logic as before)
        facing_angle = getattr(shooter_agent, 'direction', 0) # Default to stored direction
        current_target = getattr(shooter_agent, 'locked_target', None)
        if current_target:
            target_x, target_y = current_target.position
            dx = target_x - shooter_x
            dy = target_y - shooter_y
            if dx != 0 or dy != 0: facing_angle = math.atan2(dy, dx)
        elif hasattr(shooter_agent, 'velocity'):
            vx, vy = shooter_agent.velocity
            if vx != 0 or vy != 0: facing_angle = math.atan2(vy, vx)

        vision_angle_rad = math.radians(vision_angle)
        start_angle = facing_angle - vision_angle_rad / 2
        end_angle = facing_angle + vision_angle_rad / 2
        num_rays = 60
        polygon_points = [(screen_shooter_x, screen_shooter_y)]

        for i in range(num_rays):
            ray_angle = start_angle + (end_angle - start_angle) * i / (num_rays - 1)
            # Cast ray checking against ALL obstacles
            ray_endpoint = cast_ray(
                shooter_agent.position, ray_angle, max_vision_distance, all_obstacles
            )
            screen_endpoint = (int(ray_endpoint[0] * self.scale_factor), int(ray_endpoint[1] * self.scale_factor))
            polygon_points.append(screen_endpoint)

        # Draw the vision cone polygon
        if len(polygon_points) > 2:
            pygame.draw.polygon(temp_surface, (255, 255, 0, 60), polygon_points) # Semi-transparent yellow fill
            pygame.draw.polygon(temp_surface, (255, 255, 0, 120), polygon_points, 1) # Outline

        # Draw facing direction line
        dir_len = 20 * self.scale_factor # Length of direction line
        dir_endpoint = (
            screen_shooter_x + math.cos(facing_angle) * dir_len,
            screen_shooter_y + math.sin(facing_angle) * dir_len
        )
        pygame.draw.line(temp_surface, (255, 255, 0, 200), (screen_shooter_x, screen_shooter_y), dir_endpoint, 2)

        # Highlight target if within cone (optional, can be redundant)
        # ... (Target highlighting logic can be added back if desired) ...

        self.screen.blit(temp_surface, (0, 0))


    def visualize_safe_spawn_areas(self):
         """Visualize the areas where agents can safely spawn (not in wall Rects)."""
         temp_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
         grid_step = 10

         for x in range(0, self.model.width, grid_step):
             for y in range(0, self.model.height, grid_step):
                 # Check if point collides with any *physical* wall Rect
                 is_in_wall = any(wall_rect.collidepoint(x, y) for wall_rect in self.model.walls) # Check only walls

                 screen_x = int(x * self.scale_factor)
                 screen_y = int(y * self.scale_factor)
                 # Red if inside wall, faint green otherwise
                 color = (255, 0, 0, 100) if is_in_wall else (0, 255, 0, 40)
                 radius = 3
                 pygame.draw.circle(temp_surface, color, (screen_x, screen_y), radius)

         self.screen.blit(temp_surface, (0, 0))

    def draw_alert(self):
        """Draw an alert message on the screen"""
        if not self.show_alert: return

        current_time = time.time()
        if current_time - self.alert_start_time > self.alert_duration:
            self.show_alert = False
            return

        text_surface = self.alert_font.render(self.alert_message, True, self.COLORS["WHITE"])
        text_rect = text_surface.get_rect()
        alert_width = text_rect.width + 40
        alert_height = text_rect.height + 20
        alert_x = (self.screen_width - alert_width) // 2
        alert_y = 100
        alert_surface = pygame.Surface((alert_width, alert_height), pygame.SRCALPHA)

        elapsed = current_time - self.alert_start_time
        pulse_factor = 0.5 + 0.5 * math.sin(elapsed * 10)
        alpha = int(180 + 75 * pulse_factor)

        pygame.draw.rect(alert_surface, (255, 0, 0, alpha), pygame.Rect(0, 0, alert_width, alert_height), border_radius=10)
        text_x = (alert_width - text_rect.width) // 2
        text_y = (alert_height - text_rect.height) // 2
        alert_surface.blit(text_surface, (text_x, text_y))
        pygame.draw.rect(alert_surface, (255, 255, 255, 255), pygame.Rect(0, 0, alert_width, alert_height), width=2, border_radius=10)

        self.screen.blit(alert_surface, (alert_x, alert_y))

    def render_frame(self, simulation_time, sim_speed, fps=0, show_vision=False, show_safe_areas=False): # Renamed show_line_of_sight to show_vision
        """Render a complete frame of the simulation."""
        # Draw background (includes walls and doors)
        self.screen.blit(self.background, (0, 0))

        self.check_shooter_status()

        if show_safe_areas:
            self.visualize_safe_spawn_areas()

        # --- Draw Exits (Green Rects) ---
        # Draw AFTER background but BEFORE agents
        exit_color = (0, 255, 0, 150) # Semi-transparent green
        exit_border_color = (0, 100, 0) # Darker green border
        for exit_rect in self.model.exits:
             scaled_rect = pygame.Rect(
                 int(exit_rect.left * self.scale_factor), int(exit_rect.top * self.scale_factor),
                 int(exit_rect.width * self.scale_factor + 0.5), int(exit_rect.height * self.scale_factor + 0.5)
             )
             pygame.draw.rect(self.screen, exit_color, scaled_rect)
             pygame.draw.rect(self.screen, exit_border_color, scaled_rect, 1)
        # ----------------------------------

        # Pre-calculate agent draw lists
        circles_to_draw = []
        lines_to_draw = []
        for agent in self.model.schedule:
            x, y = agent.position
            screen_x = int(x * self.scale_factor)
            screen_y = int(y * self.scale_factor)
            scaled_radius = max(1, int(agent.radius * self.scale_factor))

            # Determine agent color
            if agent.agent_type == "student":
                 if getattr(agent, "is_shooter", False): color = self.COLORS["GREEN"]
                 elif getattr(agent, "has_weapon", False): color = self.COLORS["ARMED_STUDENT"]
                 elif getattr(agent, "in_emergency", False): color = (0, 100, 255) # Darker blue for fleeing
                 else: color = self.COLORS["BLUE"]
            else: # adult
                 if getattr(agent, "has_weapon", False): color = (255, 255, 0) # Yellow armed
                 elif getattr(agent, "aware_of_shooter", False): color = (255,100,0) # Orange aware
                 else: color = self.COLORS["RED"] # Default adult

            circles_to_draw.append((color, (screen_x, screen_y), scaled_radius))

            # Agent direction line
            if hasattr(agent, "velocity"):
                vx, vy = agent.velocity
                speed_squared = vx*vx + vy*vy
                if speed_squared > 0.01:
                     speed = math.sqrt(speed_squared)
                     if speed > 0:
                          dir_len = scaled_radius + 2
                          direction_x = vx / speed * dir_len
                          direction_y = vy / speed * dir_len
                          lines_to_draw.append(
                              (self.COLORS["BLACK"], (screen_x, screen_y),
                              (int(screen_x + direction_x), int(screen_y + direction_y)), 1)
                          )

        # Draw agents and direction lines
        for color, pos, radius in circles_to_draw: pygame.draw.circle(self.screen, color, pos, radius)
        for color, start, end, width in lines_to_draw: pygame.draw.line(self.screen, color, start, end, width)


        # Visualize vision cone if enabled
        if show_vision:
            self.visualize_vision_cone() # Call the cone visualization

        # Process and draw active shots
        shot_duration = config.SHOT_VISUALIZATION_DURATION
        shots_to_remove = []
        current_sim_time = self.model.simulation_time
        for i, shot in enumerate(self.model.active_shots):
             if current_sim_time - shot['start_time'] < shot_duration:
                 start_x, start_y = shot['start_pos']
                 end_x, end_y = shot['end_pos']
                 screen_start = (int(start_x * self.scale_factor), int(start_y * self.scale_factor))
                 screen_end = (int(end_x * self.scale_factor), int(end_y * self.scale_factor))
                 pygame.draw.line(self.screen, (255, 0, 0), screen_start, screen_end, 2) # Red shot line
             else: shots_to_remove.append(i)
        for i in sorted(shots_to_remove, reverse=True):
             if i < len(self.model.active_shots): self.model.active_shots.pop(i)

        # Draw UI text
        student_count = sum(1 for agent in self.model.schedule if agent.agent_type == "student")
        adult_count = sum(1 for agent in self.model.schedule if agent.agent_type == "adult")
        shooter_count = len(self.model.active_shooters)

        time_text = self.font.render(f"Sim Time: {simulation_time:.1f}s", True, self.COLORS["BLACK"])
        speed_text = self.font.render(f"Speed: {sim_speed:.1f}x", True, self.COLORS["BLACK"])
        count_text = self.font.render(f"Students: {student_count}, Adults: {adult_count}", True, self.COLORS["BLACK"])
        fps_text = self.font.render(f"FPS: {fps:.1f}", True, self.COLORS["BLACK"])
        shooter_text_color = self.COLORS["ALERT"] if shooter_count > 0 else self.COLORS["BLACK"]
        shooter_text = self.font.render(f"Active Shooters: {shooter_count}", True, shooter_text_color)

        # Update visualization status text
        vision_status = "ON" if show_vision else "OFF"
        safe_status = "ON" if show_safe_areas else "OFF"
        viz_status_text = self.font.render(
            f"Vision Cone: {vision_status} | Safe Areas: {safe_status}", # Changed 'Line of Sight' to 'Vision Cone'
            True, self.COLORS["BLACK"]
        )

        # Blit UI elements
        text_y_pos = 10
        line_height = 30
        self.screen.blit(time_text, (10, text_y_pos))
        text_y_pos += line_height
        self.screen.blit(speed_text, (10, text_y_pos))
        text_y_pos += line_height
        self.screen.blit(count_text, (10, text_y_pos))
        text_y_pos += line_height
        self.screen.blit(shooter_text, (10, text_y_pos))
        text_y_pos += line_height
        self.screen.blit(fps_text, (10, text_y_pos))
        text_y_pos += line_height
        self.screen.blit(viz_status_text, (10, text_y_pos))

        # Help text at the bottom
        self.screen.blit(self.help_text, (10, self.screen_height - 50))
        self.screen.blit(self.viz_help_text, (10, self.screen_height - 25))

        # Draw alert if active
        self.draw_alert()

        # Update display
        pygame.display.flip()