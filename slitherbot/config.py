"""Configuration utilities for the Slither bot."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Tuple
from typing import Iterable, List, Tuple


class StrategyMode(str, Enum):
    """Supported modes the bot can run in."""

    FARM = "farm"
    HUNT = "hunt"
    SURVIVAL = "survival"


@dataclass(slots=True)
class MovementTuning:
    """Fine tuning parameters for motion heuristics."""

    base_speed: float = 2.5
    boost_speed: float = 4.5
    turning_rate: float = 180.0  # degrees per second
    dodge_distance: float = 45.0  # units to consider for evasion
    food_scan_radius: float = 180.0
    aggression_threshold: float = 220.0
    retreat_threshold: float = 75.0


@dataclass(slots=True)
class SensorTuning:
    """Parameters controlling awareness of the map."""

    history_length: int = 8
    snake_tracking_radius: float = 260.0
    enemy_prediction_horizon: float = 1.4
    food_decay_seconds: float = 6.0
    hazard_scan_angle: float = 120.0


@dataclass(slots=True)
class BotConfig:
    """High level configuration for the Slither bot."""

    server_url: str = "ws://localhost:4444"
    nickname: str = "BOT"
    mode: StrategyMode = StrategyMode.FARM
    reconnect_attempts: int = 5
    reconnect_backoff: float = 2.0
    heartbeat_interval: float = 3.5
    send_rate_limit: float = 0.03
    movement_tuning: MovementTuning = field(default_factory=MovementTuning)
    sensor_tuning: SensorTuning = field(default_factory=SensorTuning)
    forbidden_names: Tuple[str, ...] = ("admin", "moderator")
    preferred_targets: Tuple[str, ...] = tuple()
    plugins: List[str] = field(default_factory=list)

    def sanitized_nickname(self) -> str:
        """Return a nickname adjusted to avoid forbidden names."""

        lowered = self.nickname.lower()
        if any(bad in lowered for bad in self.forbidden_names):
            return "BOT" if "bot" not in lowered else f"{self.nickname}_1"
        return self.nickname

    @classmethod
    def from_iterable(cls, args: Iterable[str]) -> Dict[str, Any]:
        """Create configuration keyword arguments from CLI style overrides."""

        kwargs: Dict[str, Any] = {}
    def from_iterable(cls, args: Iterable[str]) -> "BotConfig":
        """Create a configuration from CLI style key=value arguments."""

        kwargs = {}
        for item in args:
            if "=" not in item:
                raise ValueError(f"Invalid configuration override: {item}")
            key, value = item.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key == "mode":
                kwargs[key] = StrategyMode(value)
            elif key in {"reconnect_attempts"}:
                kwargs[key] = int(value)
            elif key in {
                "reconnect_backoff",
                "heartbeat_interval",
                "send_rate_limit",
            }:
                kwargs[key] = float(value)
            else:
                kwargs[key] = value
        return kwargs
        return cls(**kwargs)
