"""Top level package for the Slither automation bot."""

from .bot import SlitherBot
from .config import BotConfig, StrategyMode

__all__ = ["SlitherBot", "BotConfig", "StrategyMode"]
