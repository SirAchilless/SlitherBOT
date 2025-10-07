"""Game state tracking for the Slither bot."""
from __future__ import annotations

from dataclasses import dataclass, field
from math import atan2, cos, hypot, sin
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np


@dataclass(slots=True)
class Vector2:
    x: float
    y: float

    def __iter__(self):
        return iter((self.x, self.y))

    def distance_to(self, other: "Vector2") -> float:
        return hypot(self.x - other.x, self.y - other.y)

    def angle_to(self, other: "Vector2") -> float:
        return np.degrees(atan2(other.y - self.y, other.x - self.x)) % 360.0

    def moved_towards(self, heading_deg: float, distance: float) -> "Vector2":
        rad = np.radians(heading_deg)
        return Vector2(self.x + cos(rad) * distance, self.y + sin(rad) * distance)

    def lerp(self, other: "Vector2", alpha: float) -> "Vector2":
        return Vector2(self.x + (other.x - self.x) * alpha, self.y + (other.y - self.y) * alpha)


@dataclass(slots=True)
class Food:
    position: Vector2
    mass: float
    created: float


@dataclass(slots=True)
class Snake:
    id: str
    position: Vector2
    heading: float
    length: float
    speed: float
    is_self: bool = False
    name: Optional[str] = None

    def predicted_position(self, delta_seconds: float) -> Vector2:
        return self.position.moved_towards(self.heading, self.speed * delta_seconds)


@dataclass(slots=True)
class Hazard:
    """Regions that the bot should avoid."""

    center: Vector2
    radius: float
    expires: float


@dataclass(slots=True)
class GameState:
    """Mutable representation of the known game world."""

    tick: int = 0
    snakes: Dict[str, Snake] = field(default_factory=dict)
    foods: List[Food] = field(default_factory=list)
    hazards: List[Hazard] = field(default_factory=list)
    world_size: Tuple[int, int] = (1200, 1200)

    def self_snake(self) -> Optional[Snake]:
        return next((snake for snake in self.snakes.values() if snake.is_self), None)

    def update_food(self, foods: Iterable[Food]) -> None:
        self.foods.extend(foods)
        self.foods.sort(key=lambda f: f.mass, reverse=True)

    def decay_food(self, now: float, decay_seconds: float) -> None:
        self.foods = [food for food in self.foods if now - food.created <= decay_seconds]

    def update_snakes(self, snakes: Iterable[Snake]) -> None:
        for snake in snakes:
            self.snakes[snake.id] = snake

    def remove_snake(self, snake_id: str) -> None:
        self.snakes.pop(snake_id, None)

    def prune_hazards(self, now: float) -> None:
        self.hazards = [hazard for hazard in self.hazards if hazard.expires > now]

    def mark_hazard(self, center: Vector2, radius: float, expires: float) -> None:
        self.hazards.append(Hazard(center=center, radius=radius, expires=expires))

    def nearest_food(self, origin: Vector2) -> Optional[Food]:
        return min(self.foods, key=lambda food: origin.distance_to(food.position), default=None)

    def threats_in_radius(self, origin: Vector2, radius: float) -> List[Snake]:
        return [snake for snake in self.snakes.values() if not snake.is_self and origin.distance_to(snake.position) <= radius]

    def best_target(self, origin: Vector2, preferred_names: Tuple[str, ...]) -> Optional[Snake]:
        candidates = [snake for snake in self.snakes.values() if not snake.is_self]
        if not candidates:
            return None
        weights: List[Tuple[float, Snake]] = []
        for snake in candidates:
            distance = origin.distance_to(snake.position)
            preference_bonus = 0.0
            if snake.name:
                lowered = snake.name.lower()
                if any(pref.lower() in lowered for pref in preferred_names):
                    preference_bonus = 1.5
            weight = (snake.length / max(distance, 1.0)) + preference_bonus
            weights.append((weight, snake))
        weights.sort(key=lambda item: item[0], reverse=True)
        return weights[0][1]


def blend_headings(current: float, target: float, rate: float, dt: float) -> float:
    """Return a heading that smoothly approaches the target."""

    diff = (target - current + 540.0) % 360.0 - 180.0
    max_step = rate * dt
    if abs(diff) <= max_step:
        return target
    return (current + max_step * np.sign(diff)) % 360.0
