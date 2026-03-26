"""Shared pytest fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from Engine.models import MarketQuote, MarketSnapshot


@pytest.fixture
def btc_eth_snapshot() -> MarketSnapshot:
    t = datetime.now(UTC)
    return MarketSnapshot(
        fetched_at=t,
        quotes={
            "BTC": MarketQuote(
                price=Decimal("50000"),
                volume=Decimal("1000"),
                ts=t,
            ),
            "ETH": MarketQuote(
                price=Decimal("3000"),
                volume=Decimal("8000"),
                ts=t,
            ),
        },
        source_meta={"type": "test"},
    )
