"""Decision planner combining strategies with heuristics."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from .config import BotConfig
from .state import GameState, Snake, Vector2, blend_headings
from .strategies import BaseStrategy, StrategyDecision


@dataclass(slots=True)
class PlannedAction:
    heading: float
    boost: bool
    throttle: float
    target: Optional[Vector2]
    reason: str


class ActionPlanner:
    """Refines strategic decisions into low level commands."""

    def __init__(self, config: BotConfig, strategy: BaseStrategy) -> None:
        self.config = config
        self.strategy = strategy
        self._last_heading: float = 0.0
        self._last_plan: Optional[PlannedAction] = None
        self._last_time = time.monotonic()

    def step(self, state: GameState, now: float) -> PlannedAction:
        decision = self.strategy.select(state, now)
        snake = state.self_snake()
        if not snake:
            return PlannedAction(heading=self._last_heading, boost=False, throttle=0.0, target=None, reason="waiting")

        dt = max(now - self._last_time, 1e-3)
        heading = blend_headings(
            self._last_heading or snake.heading,
            decision.heading,
            self.config.movement_tuning.turning_rate,
            dt,
        )
        throttle = self.config.movement_tuning.boost_speed if decision.boost else self.config.movement_tuning.base_speed

        plan = PlannedAction(heading=heading, boost=decision.boost, throttle=throttle, target=decision.target, reason=decision.reason)
        self._last_heading = heading
        self._last_plan = plan
        self._last_time = now
        return plan

    @property
    def last_plan(self) -> Optional[PlannedAction]:
        return self._last_plan

    def update_strategy(self, strategy: BaseStrategy) -> None:
        self.strategy = strategy
