"""Maps persisted strategy keys to `BaseBot` implementations (plug-in registry)."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from Engine.bots.aggressive_bot import AggressiveBot
from Engine.bots.base_bot import BaseBot
from Engine.bots.passive_bot import PassiveBot
from Engine.bots.smart_bot import SmartBot

if TYPE_CHECKING:
    from Database.models import Bot as BotRow


class StrategyRegistry:
    """Central registry for strategy name → bot class. Extend via `register`."""

    _map: ClassVar[dict[str, type[BaseBot]]] = {
        "aggressive": AggressiveBot,
        "passive": PassiveBot,
        "smart": SmartBot,
    }

    @classmethod
    def register(cls, name: str, bot_cls: type[BaseBot]) -> None:
        cls._map[name.strip().lower()] = bot_cls

    @classmethod
    def resolve(cls, strategy: str) -> type[BaseBot]:
        key = strategy.lower().strip()
        bot_cls = cls._map.get(key)
        if bot_cls is None:
            msg = f"Unknown strategy {strategy!r}; register a class with StrategyRegistry.register."
            raise ValueError(msg)
        return bot_cls

    @classmethod
    def build_bot(cls, row: BotRow) -> BaseBot:
        bot_cls = cls.resolve(row.strategy)
        return bot_cls(bot_id=row.id, name=row.name)


def build_bot(row: BotRow) -> BaseBot:
    """Backward-compatible helper."""
    return StrategyRegistry.build_bot(row)


def register_strategy(name: str, cls: type[BaseBot]) -> None:
    """Register a new plug-in bot type at runtime."""
    StrategyRegistry.register(name, cls)
