"""Command line entry point for running the Slither bot."""
from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import replace
from typing import Iterable

from .bot import SlitherBot
from .config import BotConfig, StrategyMode, parse_config_overrides


def parse_arguments(argv: Iterable[str] | None = None) -> BotConfig:
    parser = argparse.ArgumentParser(description="Run the Slither automation bot")
    parser.add_argument("server", help="Websocket URL of the Slither server")
    parser.add_argument("nickname", help="Nickname to use for the bot")
    parser.add_argument(
        "--mode",
        default=StrategyMode.FARM.value,
        choices=[mode.value for mode in StrategyMode],
        help="Initial strategy mode",
    )
    parser.add_argument(
        "--config",
        nargs="*",
        default=(),
        help="Extra key=value overrides (e.g. reconnect_attempts=10)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    config = BotConfig(server_url=args.server, nickname=args.nickname, mode=StrategyMode(args.mode))
    if args.config:
        overrides = parse_config_overrides(args.config)
        config = replace(config, **overrides)
    return config


def main(argv: Iterable[str] | None = None) -> None:
    config = parse_arguments(argv)
    bot = SlitherBot(config)
    asyncio.run(bot.run())


if __name__ == "__main__":  # pragma: no cover
    main()
