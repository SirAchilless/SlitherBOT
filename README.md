# SlitherBOT

A modular Python automation bot for [slither.io](https://slither.io/) style servers. The bot connects to a WebSocket endpoint, keeps track of the world state and selects actions using configurable strategies such as farming, hunting and survival.

> **Note**: The provided protocol assumes a JSON-based self-hosted server used for testing purposes. When targeting the original slither.io protocol, a translation layer is required because the official servers use a custom binary format.

## Features

- 🧠 **Strategy modes**: farm (passive growth), hunt (aggressive targeting) and survival (defensive play). Modes can be switched on-the-fly through server messages.
- 🛰️ **State tracking**: continuously updates knowledge about snakes, food pellets and temporary hazards.
- 🚀 **Responsive movement**: smooth heading interpolation and configurable boost usage for fast reflexes.
- 🔌 **Plugin hooks**: register custom plugins to react to bot events or implement additional behaviours.
- 🔁 **Robust connection handling**: automatic heartbeat, reconnection backoff and rate-limited command dispatch.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Running the bot

```bash
slitherbot ws://127.0.0.1:4444 "SneakyBot" --mode hunt --config heartbeat_interval=2.0 send_rate_limit=0.05
```

The `--config` option accepts additional `key=value` overrides for any `BotConfig` field.

## Integrating with a server

The reference implementation expects the following JSON messages over WebSocket:

### Server → Bot

- `{"type": "world", "payload": {"size": [width, height]}}`
- `{"type": "snake", "payload": {"id": "unique", "x": 100, "y": 200, "heading": 90, "length": 120, "speed": 4.5, "self": false, "name": "enemy"}}`
- `{"type": "snake_leave", "payload": {"id": "unique"}}`
- `{"type": "food_batch", "payload": {"items": [[x, y, mass], ...]}}`
- `{"type": "hazard", "payload": {"x": 100, "y": 40, "radius": 30, "duration": 1.5}}`
- `{"type": "mode", "payload": {"value": "hunt"}}`

### Bot → Server

- `{"type": "join", "payload": {"nickname": "SneakyBot"}}`
- `{"type": "heartbeat", "payload": {"time": 1690000000.0}}`
- `{"type": "move", "payload": {"heading": 90.0, "boost": true, "throttle": 4.5, "reason": "hunt"}}`

These messages are easy to adapt to a custom self-hosted environment. When interfacing with the official servers, replace `slitherbot.protocol.SlitherProtocol` with one that speaks the binary protocol and converts messages into the structures understood by the bot.

## Extending the bot

Create a plugin by inheriting from `slitherbot.bot.BasePlugin` and registering it with `SlitherBot.register_plugin`. Plugins receive asynchronous events via `handle` and can be used for telemetry, adaptive tuning or external controls.

Strategy logic can be customised by implementing a new class derived from `slitherbot.strategies.BaseStrategy` and swapping it at runtime using `SlitherBot.set_mode` or by calling `ActionPlanner.update_strategy` directly.

## Development

```bash
pip install -e .[dev]
pytest
```

Tests are not included by default but the project structure is ready for unit testing (e.g. mocking the protocol and validating planner behaviour).

## License

MIT
