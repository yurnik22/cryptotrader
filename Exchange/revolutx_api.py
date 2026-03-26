"""Revolut X adapter — stub, optional synthetic quotes, or future live HTTP."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from Engine.models import MarketSnapshot

if TYPE_CHECKING:
    from Exchange.mock_exchange import MockExchange

logger = logging.getLogger("cryptotrader.exchange.revolut")


class RevolutXAdapter:
    """Implements `ExchangeInterface`; live trading wiring is intentionally isolated here."""

    def __init__(
        self,
        *,
        api_base: str,
        api_key: str | None,
        stub_exchange: MockExchange | None,
    ) -> None:
        self._api_base = api_base.rstrip("/")
        self._api_key = api_key
        self._stub = stub_exchange

    async def get_market_snapshot(self, symbols: list[str]) -> MarketSnapshot:
        if self._stub is not None:
            snap = await self._stub.get_market_snapshot(symbols)
            meta = dict(snap.source_meta)
            meta["revolut_mode"] = "stub"
            return MarketSnapshot(
                fetched_at=snap.fetched_at,
                quotes=snap.quotes,
                source_meta=meta,
            )

        if not self._api_key or not self._api_base:
            logger.error("revolut_live_not_configured")
            raise RuntimeError(
                "Revolut X live mode requires api_base, CRYPTOTRADER_REVOLUT_API_KEY, "
                "and revolut.use_stub: false — see config.yaml.example."
            )

        # Placeholder for httpx/aiohttp integration when API contract is finalized.
        raise NotImplementedError(
            "Revolut X HTTP snapshot fetch is not implemented yet; "
            "set revolut.use_stub: true for paper-style quotes."
        )
