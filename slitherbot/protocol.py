"""Minimal WebSocket protocol helpers for communicating with a Slither server."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional

import websockets

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class IncomingMessage:
    type: str
    payload: Dict[str, Any]


class SlitherProtocol:
    """Handles the websocket communication with a slither-like server."""

    def __init__(self, uri: str, heartbeat_interval: float) -> None:
        self._uri = uri
        self._heartbeat_interval = heartbeat_interval
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._receiver_task: Optional[asyncio.Task[None]] = None
        self._queue: asyncio.Queue[IncomingMessage] = asyncio.Queue()
        self._stop = asyncio.Event()

    async def __aenter__(self) -> "SlitherProtocol":
        LOGGER.info("Connecting to %s", self._uri)
        self._ws = await websockets.connect(self._uri, max_size=2 ** 23)
        self._stop.clear()
        self._receiver_task = asyncio.create_task(self._receiver())
        asyncio.create_task(self._heartbeat())
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        if self._receiver_task:
            self._stop.set()
            await self._receiver_task
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def _receiver(self) -> None:
        assert self._ws is not None
        try:
            async for raw_message in self._ws:
                try:
                    data = json.loads(raw_message)
                except json.JSONDecodeError:
                    LOGGER.warning("Unparseable message: %s", raw_message)
                    continue
                message_type = data.get("type", "unknown")
                payload = data.get("payload", {})
                await self._queue.put(IncomingMessage(type=message_type, payload=payload))
        except websockets.ConnectionClosed as exc:
            LOGGER.warning("Connection closed: %s", exc)
        finally:
            await self._queue.put(IncomingMessage(type="disconnect", payload={}))

    async def _heartbeat(self) -> None:
        assert self._ws is not None
        while not self._stop.is_set():
            try:
                await asyncio.sleep(self._heartbeat_interval)
                await self.send({"type": "heartbeat", "payload": {"time": time.time()}})
            except asyncio.CancelledError:  # pragma: no cover - cooperative cancellation
                break
            except Exception as exc:  # pragma: no cover - network errors
                LOGGER.error("Heartbeat failure: %s", exc)
                break

    async def send(self, message: Dict[str, Any]) -> None:
        if not self._ws:
            raise RuntimeError("WebSocket is not connected")
        await self._ws.send(json.dumps(message))

    async def messages(self) -> AsyncIterator[IncomingMessage]:
        while True:
            message = await self._queue.get()
            yield message
            if message.type == "disconnect":
                break
