"""Exchange abstraction — bots must not depend on concrete implementations."""

from __future__ import annotations

from typing import Protocol

from Engine.models import MarketSnapshot


class ExchangeInterface(Protocol):
    async def get_market_snapshot(self, symbols: list[str]) -> MarketSnapshot: ...
