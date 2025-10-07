"""Strategy implementations for different bot behaviours."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Optional

from .config import BotConfig, StrategyMode
from .state import GameState, Snake, Vector2, blend_headings


@dataclass(slots=True)
class StrategyDecision:
    heading: float
    boost: bool
    target: Optional[Vector2] = None
    reason: str = "idle"


class BaseStrategy:
    """Common logic shared by every strategy."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.last_reason = "startup"

    def _default_decision(self, snake: Snake) -> StrategyDecision:
        return StrategyDecision(heading=snake.heading, boost=False, target=None, reason="hold")

    def select(self, state: GameState, now: float) -> StrategyDecision:
        snake = state.self_snake()
        if not snake:
            return StrategyDecision(heading=0.0, boost=False, target=None, reason="no-self")
        return self._select(state, snake, now)

    def _select(self, state: GameState, snake: Snake, now: float) -> StrategyDecision:  # pragma: no cover - abstract
        raise NotImplementedError


class FarmStrategy(BaseStrategy):
    def _select(self, state: GameState, snake: Snake, now: float) -> StrategyDecision:
        food = state.nearest_food(snake.position)
        if food:
            heading = snake.position.angle_to(food.position)
            return StrategyDecision(heading=heading, boost=False, target=food.position, reason="food")
        world_w, world_h = state.world_size
        center = Vector2(world_w / 2, world_h / 2)
        heading = blend_headings(snake.heading, snake.position.angle_to(center), self.config.movement_tuning.turning_rate, 0.05)
        return StrategyDecision(heading=heading, boost=False, target=center, reason="center")


class HuntStrategy(BaseStrategy):
    def _select(self, state: GameState, snake: Snake, now: float) -> StrategyDecision:
        target = state.best_target(snake.position, self.config.preferred_targets)
        if target is None:
            return FarmStrategy(self.config)._select(state, snake, now)
        heading = snake.position.angle_to(target.position)
        distance = snake.position.distance_to(target.position)
        boost = distance < self.config.movement_tuning.aggression_threshold
        return StrategyDecision(heading=heading, boost=boost, target=target.position, reason="hunt")


class SurvivalStrategy(BaseStrategy):
    def _select(self, state: GameState, snake: Snake, now: float) -> StrategyDecision:
        threats = state.threats_in_radius(snake.position, self.config.movement_tuning.dodge_distance)
        if threats:
            mean_angle = sum(snake.position.angle_to(threat.position) for threat in threats) / len(threats)
            heading = (mean_angle + 180.0) % 360.0
            return StrategyDecision(heading=heading, boost=True, target=None, reason="evade")
        farm_decision = FarmStrategy(self.config)._select(state, snake, now)
        farm_decision.reason = "patrol"
        return farm_decision


def make_strategy(mode: StrategyMode, config: BotConfig) -> BaseStrategy:
    if mode is StrategyMode.FARM:
        return FarmStrategy(config)
    if mode is StrategyMode.HUNT:
        return HuntStrategy(config)
    if mode is StrategyMode.SURVIVAL:
        return SurvivalStrategy(config)
    raise ValueError(f"Unsupported mode: {mode}")
