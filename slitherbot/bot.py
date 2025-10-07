"""High level orchestration for the Slither bot."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Optional

from .config import BotConfig, StrategyMode
from .planner import ActionPlanner
from .protocol import IncomingMessage, SlitherProtocol
from .state import Food, GameState, Snake, Vector2
from .strategies import BaseStrategy, make_strategy

LOGGER = logging.getLogger(__name__)


class SlitherBot:
    """Entry point for connecting to a slither server and automating gameplay."""

    def __init__(self, config: Optional[BotConfig] = None) -> None:
        self.config = config or BotConfig()
        self.state = GameState()
        self._strategy: BaseStrategy = make_strategy(self.config.mode, self.config)
        self._planner = ActionPlanner(self.config, self._strategy)
        self._protocol: Optional[SlitherProtocol] = None
        self._last_send = 0.0
        self._plugins: Dict[str, BasePlugin] = {}

    async def run(self) -> None:
        """Connect to the server and enter the main update loop."""

        retries = 0
        while retries <= self.config.reconnect_attempts:
            try:
                async with SlitherProtocol(self.config.server_url, self.config.heartbeat_interval) as protocol:
                    self._protocol = protocol
                    await protocol.send(
                        {
                            "type": "join",
                            "payload": {"nickname": self.config.sanitized_nickname()},
                        }
                    )
                    await self._loop(protocol)
            except Exception as exc:
                LOGGER.exception("Bot loop error: %s", exc)
            retries += 1
            await asyncio.sleep(self.config.reconnect_backoff * retries)
            LOGGER.info("Reconnect attempt %s", retries)

    async def _loop(self, protocol: SlitherProtocol) -> None:
        async for message in protocol.messages():
            now = time.monotonic()
            await self._handle_message(message, now)
            await self._maybe_act(now)

    async def _handle_message(self, message: IncomingMessage, now: float) -> None:
        if message.type == "world" and "size" in message.payload:
            self.state.world_size = tuple(message.payload["size"])  # type: ignore[assignment]
        elif message.type == "snake" and "id" in message.payload:
            snake = Snake(
                id=str(message.payload["id"]),
                position=Vector2(message.payload.get("x", 0.0), message.payload.get("y", 0.0)),
                heading=message.payload.get("heading", 0.0),
                length=message.payload.get("length", 0.0),
                speed=message.payload.get("speed", self.config.movement_tuning.base_speed),
                is_self=message.payload.get("self", False),
                name=message.payload.get("name"),
            )
            self.state.update_snakes([snake])
        elif message.type == "snake_leave":
            self.state.remove_snake(str(message.payload.get("id")))
        elif message.type == "food_batch":
            foods = [
                Food(
                    position=Vector2(item[0], item[1]),
                    mass=item[2],
                    created=now,
                )
                for item in message.payload.get("items", [])
            ]
            self.state.update_food(foods)
        elif message.type == "hazard":
            self.state.mark_hazard(
                center=Vector2(message.payload.get("x", 0.0), message.payload.get("y", 0.0)),
                radius=message.payload.get("radius", 20.0),
                expires=now + message.payload.get("duration", 2.0),
            )
        elif message.type == "mode":
            mode = StrategyMode(message.payload.get("value", self.config.mode.value))
            self.set_mode(mode)
        self.state.decay_food(now, self.config.sensor_tuning.food_decay_seconds)
        self.state.prune_hazards(now)

    async def _maybe_act(self, now: float) -> None:
        if not self._protocol:
            return
        if now - self._last_send < self.config.send_rate_limit:
            return
        plan = self._planner.step(self.state, now)
        message = {
            "type": "move",
            "payload": {
                "heading": plan.heading,
                "boost": plan.boost,
                "throttle": plan.throttle,
                "reason": plan.reason,
            },
        }
        await self._protocol.send(message)
        self._last_send = now

    def set_mode(self, mode: StrategyMode) -> None:
        LOGGER.info("Switching mode to %s", mode.value)
        self.config.mode = mode
        self._strategy = make_strategy(mode, self.config)
        self._planner.update_strategy(self._strategy)

    def register_plugin(self, plugin: "BasePlugin") -> None:
        self._plugins[plugin.name] = plugin
        plugin.on_register(self)

    async def emit_event(self, event: str, **payload) -> None:
        for plugin in self._plugins.values():
            await plugin.handle(event, **payload)


class BasePlugin:
    name = "base"

    def on_register(self, bot: SlitherBot) -> None:  # pragma: no cover - interface
        self.bot = bot

    async def handle(self, event: str, **payload) -> None:  # pragma: no cover - interface
        pass
