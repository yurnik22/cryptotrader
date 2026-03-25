"""Abstract bot — decision maker only; no exchange or DB access."""

from __future__ import annotations

from abc import ABC, abstractmethod

from Engine.models import BotContext, Decision, MarketSnapshot


class BaseBot(ABC):
    def __init__(self, *, bot_id: int, name: str) -> None:
        self.bot_id = bot_id
        self.name = name

    @abstractmethod
    async def decide(self, context: BotContext, snapshot: MarketSnapshot) -> Decision:
        """Return the next action using only context + shared snapshot."""
