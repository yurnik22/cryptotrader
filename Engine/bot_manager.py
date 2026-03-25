"""Maps DB strategy keys to bot implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from Engine.bots.aggressive_bot import AggressiveBot
from Engine.bots.base_bot import BaseBot
from Engine.bots.passive_bot import PassiveBot
from Engine.bots.smart_bot import SmartBot

if TYPE_CHECKING:
    from Database.models import Bot as BotRow

_STRATEGY_MAP: dict[str, type[BaseBot]] = {
    "aggressive": AggressiveBot,
    "passive": PassiveBot,
    "smart": SmartBot,
}


def build_bot(row: BotRow) -> BaseBot:
    key = row.strategy.lower().strip()
    cls = _STRATEGY_MAP.get(key)
    if cls is None:
        msg = f"Unknown strategy {row.strategy!r}; add a bot class and register it."
        raise ValueError(msg)
    return cls(bot_id=row.id, name=row.name)


def register_strategy(name: str, cls: type[BaseBot]) -> None:
    """Register a new plug-in bot type at runtime."""
    _STRATEGY_MAP[name.lower()] = cls
