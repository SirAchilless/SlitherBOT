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

On Windows PowerShell use:

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -e .
```

On `cmd.exe` the activation step becomes `\.venv\\Scripts\\activate.bat`.

> **Tip**: The trailing dot (`pip install -e .`) tells pip to install the
> project in the current directory. Omitting it results in the error
> `-e option requires 1 argument`.

## Running the bot

```bash
slitherbot ws://127.0.0.1:4444 "SneakyBot" --mode hunt --config heartbeat_interval=2.0 send_rate_limit=0.05
```

If the `slitherbot` command is not found on Windows, explicitly invoke the script from the
virtual environment or run the package as a module:

```powershell
.venv\Scripts\slitherbot.exe ws://127.0.0.1:4444 "SneakyBot" --mode hunt
python -m slitherbot ws://127.0.0.1:4444 "SneakyBot" --mode hunt
```

The `--config` option accepts additional `key=value` overrides for any `BotConfig` field.

> **Windows note**: If you recently pulled an update and still encounter
> `BotConfig.from_iterable() missing 1 required positional argument: 'args'`,
> re-run `pip install -e .` inside your virtual environment. This refreshes the
> console launcher so that configuration overrides are parsed correctly. You can
> always bypass the launcher altogether with `python -m slitherbot ...`.

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
