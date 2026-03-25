"""Placeholder Revolut X adapter — wire in main/factory when live trading is ready."""

from __future__ import annotations

from Engine.models import MarketSnapshot


class RevolutXAdapter:
    """Stub implementing the exchange protocol; does not call external APIs."""

    async def get_market_snapshot(self, symbols: list[str]) -> MarketSnapshot:
        raise NotImplementedError(
            "RevolutXAdapter.get_market_snapshot is not implemented; use MockExchange for paper mode."
        )
