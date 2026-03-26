"""Paper-trading exchange: generates coherent snapshots with Decimal prices."""

from __future__ import annotations

import random
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from Engine.models import MarketQuote, MarketSnapshot


class MockExchange:
    """Config-driven quotes with optional Decimal random walk per snapshot (exchange-side only)."""

    def __init__(
        self,
        *,
        base_prices: dict[str, Decimal],
        base_volumes: dict[str, Decimal],
        price_noise_bps: Decimal = Decimal("5"),
        rng: random.Random | None = None,
    ) -> None:
        self._base_prices = {k.upper(): v for k, v in base_prices.items()}
        self._base_volumes = {k.upper(): v for k, v in base_volumes.items()}
        self._noise_bps = price_noise_bps
        self._rng = rng or random.Random()
        self._state: dict[str, Decimal] = dict(self._base_prices)

    def _jitter_factor(self) -> Decimal:
        """Symmetric jitter in [-noise_bps, +noise_bps] as fraction of price."""
        if self._noise_bps <= 0:
            return Decimal("0")
        # Uniform in [0, 1_000_000] → [-1, 1] * (noise_bps / 10000)
        u = Decimal(self._rng.randint(0, 1_000_000))
        signed = (u / Decimal("500000")) - Decimal("1")
        return signed * (self._noise_bps / Decimal("10000"))

    async def get_market_snapshot(self, symbols: list[str]) -> MarketSnapshot:
        now = datetime.now(UTC)
        quotes: dict[str, MarketQuote] = {}
        for sym in symbols:
            key = sym.upper()
            base = self._state.get(key) or self._base_prices.get(key)
            if base is None:
                continue
            price = (base * (Decimal("1") + self._jitter_factor())).quantize(Decimal("0.00000001"))
            self._state[key] = price
            vol = self._base_volumes.get(key, Decimal("1000"))
            quotes[key] = MarketQuote(price=price, volume=vol, ts=now)
        source: dict[str, Any] = {"type": "mock", "noise_bps": str(self._noise_bps)}
        return MarketSnapshot(fetched_at=now, quotes=quotes, source_meta=source)
