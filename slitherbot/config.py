"""Configuration utilities for the Slither bot."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Tuple


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

    @staticmethod
    def from_iterable(*raw_args: Iterable[str]) -> Dict[str, Any]:
        """Backwards compatible wrapper for :func:`parse_config_overrides`.

        The function accepts ``*raw_args`` instead of a single iterable so it can
        gracefully handle two edge-cases observed on Windows:

        * Some console launchers bind the descriptor as if it were an instance
          method, providing the ``BotConfig`` class as the first positional
          argument followed by the actual iterable.
        * Other launchers correctly treat the function as a staticmethod and
          only forward the iterable.

        Normalising the incoming values keeps older console entry points (and
        cached bytecode) working after users upgrade the package without
        forcing a reinstall of the script wrapper.
        """

        if not raw_args:
            raise TypeError("BotConfig.from_iterable() missing configuration values")

        if len(raw_args) == 1:
            iterable = raw_args[0]
        elif len(raw_args) == 2 and isinstance(raw_args[0], type) and issubclass(raw_args[0], BotConfig):
            # Windows console launchers sometimes inject the class itself as the
            # first positional argument when the entry point was generated before
            # upgrading the package. Accept the second argument as the iterable.
            iterable = raw_args[1]
        else:
            raise TypeError(
                "BotConfig.from_iterable() received unexpected arguments; "
                "re-run 'pip install -e .' to refresh the console script"
            )

        return parse_config_overrides(iterable)


def parse_config_overrides(args: Iterable[str]) -> Dict[str, Any]:
    """Create configuration keyword arguments from CLI style overrides.

    Some Windows console-script launchers have been observed to mis-bind the
    ``BotConfig.from_iterable`` descriptor, handing the class itself as the
    first positional argument. Importing and calling this free function avoids
    that edge case entirely while still keeping ``BotConfig.from_iterable`` as
    a convenience wrapper for backwards compatibility.
    """

    kwargs: Dict[str, Any] = {}
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
