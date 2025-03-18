from agents.schoolagent import SchoolAgent

import math
import random


class StudentAgent(SchoolAgent):
    def __init__(self, unique_id, model, position, agent_type, agents):
        # Fix the parameter order to match SchoolAgent
        super().__init__(unique_id, model, agent_type, position, agents)

        # Student-specific attributes
        self.fear_level = 0.0
        self.grab_weapon_prob = 0.05
        self.state = "Normal"

        # Shooter-specific attributes
        self.is_shooter = False
        self.last_shot_time = 0.0
        self.shooting_interval = 2.0  # Shoot every 2 seconds
        self.shooting_range = 10.0  # Stop and shoot within 10 units
        self.hit_probability = 0.5  # 50% chance to hit

    def step_continuous(self, dt):
        """Optimized version of step_continuous with shooter behavior and wall awareness"""
        if not self.is_shooter:
            # Use standard movement for non-shooters
            super().step_continuous(dt)
            return

        # Shooter-specific behavior with line of sight
        current_time = self.model.simulation_time

        # Find visible target agents
        search_radius = max(self.shooting_range * 3, 100.0)  # Larger search radius to allow seeking targets
        nearby_agents = self.model.spatial_grid.get_nearby_agents(self.position, search_radius)

        # Filter for valid targets that are visible (not blocked by walls)
        visible_targets = []
        for agent in nearby_agents:
            if agent != self and agent.agent_type in ["student", "adult"]:
                if self.has_line_of_sight(agent.position):
                    visible_targets.append(agent)

        if not visible_targets:
            # No visible targets - move randomly to search
            self.search_behavior(dt)
        else:
            # Find nearest visible target
            nearest_agent = None
            min_distance_squared = float('inf')

            for agent in visible_targets:
                dx = self.position[0] - agent.position[0]
                dy = self.position[1] - agent.position[1]
                distance_squared = dx * dx + dy * dy

                if distance_squared < min_distance_squared:
                    min_distance_squared = distance_squared
                    nearest_agent = agent

            # Calculate actual distance only once
            distance = math.sqrt(min_distance_squared)

            if distance > self.shooting_range:
                # Move toward nearest target
                dx = nearest_agent.position[0] - self.position[0]
                dy = nearest_agent.position[1] - self.position[1]

                # Normalize direction
                inv_dist = 1.0 / distance
                direction_x = dx * inv_dist
                direction_y = dy * inv_dist

                # Set velocity directly
                self.velocity = (direction_x * self.max_speed, direction_y * self.max_speed)
            else:
                # Within shooting range - stop and attempt to shoot
                self.velocity = (0, 0)

                # Try to shoot if enough time has passed
                if current_time - self.last_shot_time >= self.shooting_interval:
                    self._shoot_at_target(nearest_agent, current_time)

        # Update position with wall collision checks
        new_x = self.position[0] + self.velocity[0] * dt
        new_y = self.position[1] + self.velocity[1] * dt

        # Keep within boundaries
        new_x = max(self.radius, min(new_x, self.model.width - self.radius))
        new_y = max(self.radius, min(new_y, self.model.height - self.radius))

        # Check for wall collisions
        if self.would_collide_with_wall((new_x, new_y)):
            # Try a reduced movement
            reduced_x = self.position[0] + (new_x - self.position[0]) * 0.1
            reduced_y = self.position[1] + (new_y - self.position[1]) * 0.1

            if not self.would_collide_with_wall((reduced_x, reduced_y)):
                new_x, new_y = reduced_x, reduced_y
            else:
                # Change direction if can't move at all
                self.direction = (self.direction + random.uniform(0.5 * math.pi, 1.5 * math.pi)) % (2 * math.pi)
                self.velocity = (
                    math.cos(self.direction) * self.max_speed * 0.5,
                    math.sin(self.direction) * self.max_speed * 0.5
                )
                return

        # Update position
        old_position = self.position
        self.position = (new_x, new_y)

        # Update spatial grid if position changed
        if old_position != self.position:
            self.model.spatial_grid.update_agent(self)

    def _shoot_at_target(self, target, current_time):
        """Execute shooting logic at a target"""
        # Record the shot
        shot = {
            'start_pos': self.position,
            'end_pos': target.position,
            'start_time': current_time
        }
        self.model.active_shots.append(shot)

        # Play sound if available
        try:
            if hasattr(self.model, 'gunshot_sound') and self.model.gunshot_sound:
                self.model.gunshot_sound.play()
        except Exception as e:
            print(f"Warning: Could not play gunshot sound: {e}")

        # Determine if shot hits
        if random.random() < self.hit_probability:
            print(f"Shooter {self.unique_id} hit agent {target.unique_id}")

            # Play kill sound if available
            try:
                if hasattr(self.model, 'kill_sound') and self.model.kill_sound:
                    self.model.kill_sound.play()
            except Exception as e:
                print(f"Warning: Could not play kill sound: {e}")

            # Remove the target from the model
            self.model.remove_agent(target)
        else:
            print(f"Shooter {self.unique_id} missed")

        # Update last shot time
        self.last_shot_time = current_time

    # Keep the rest of the methods unchanged
    def would_collide_with_wall(self, position):
        """Check if a position would collide with any wall"""
        x, y = position
        agent_radius = self.radius

        for wall in self.model.walls:
            wall_x1, wall_y1, wall_x2, wall_y2 = wall

            # Calculate distance to wall - treat walls as rectangles
            closest_x = max(wall_x1, min(x, wall_x2))
            closest_y = max(wall_y1, min(y, wall_y2))

            # If closest point is inside the wall, collision is certain
            if closest_x == x and closest_y == y and wall_x1 <= x <= wall_x2 and wall_y1 <= y <= wall_y2:
                return True

            # Calculate distance from agent center to closest point on wall
            dx = x - closest_x
            dy = y - closest_y
            distance_squared = dx * dx + dy * dy

            # Collision if distance is less than agent radius
            if distance_squared <= agent_radius * agent_radius:
                return True

        return False

    def search_behavior(self, dt):
        """Behavior for searching for targets when none are visible"""
        # Check if we've been in search mode for too long without finding a target
        search_duration_threshold = 5.0  # seconds

        # Initialize search_start_time if not set
        if not hasattr(self, 'search_start_time'):
            self.search_start_time = self.model.simulation_time
            self.search_direction_change_time = 0

        # Check if time to change direction
        if self.model.simulation_time - self.search_direction_change_time > 2.0:
            # Change direction more often when searching
            self.direction = random.uniform(0, 2 * math.pi)
            self.search_direction_change_time = self.model.simulation_time

        # Set velocity based on direction
        self.velocity = (
            math.cos(self.direction) * self.max_speed * 0.7,  # Move slower while searching
            math.sin(self.direction) * self.max_speed * 0.7
        )

        # Reset search timer if we've been searching too long
        if self.model.simulation_time - self.search_start_time > search_duration_threshold:
            self.search_start_time = self.model.simulation_time
            # More dramatic direction change after long search
            self.direction = random.uniform(0, 2 * math.pi)

    def has_line_of_sight(self, target_position):
        """
        Check if this agent has line of sight to the target position.
        Returns True if there's a clear line of sight, False if a wall blocks the view.
        """
        # Get positions
        start_x, start_y = self.position
        end_x, end_y = target_position

        # Check each wall for intersection
        for wall in self.model.walls:
            if line_intersects_rectangle(
                    start_x, start_y, end_x, end_y,
                    wall[0], wall[1], wall[2], wall[3]
            ):
                return False  # Wall blocks line of sight

        # No walls block the view
        return True


# These functions can stay outside the class
def line_intersects_rectangle(line_x1, line_y1, line_x2, line_y2,
                              rect_x1, rect_y1, rect_x2, rect_y2):
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


def point_in_rectangle(x, y, rect_x1, rect_y1, rect_x2, rect_y2):
    """Check if a point is inside a rectangle."""
    return (rect_x1 <= x <= rect_x2 and rect_y1 <= y <= rect_y2)


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