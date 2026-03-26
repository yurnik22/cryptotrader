"""Tests for MockExchange snapshot generation."""

from __future__ import annotations

from decimal import Decimal

import pytest

from Exchange.mock_exchange import MockExchange


@pytest.mark.asyncio
async def test_mock_exchange_returns_quotes_for_symbols() -> None:
    ex = MockExchange(
        base_prices={"BTC": Decimal("100"), "ETH": Decimal("10")},
        base_volumes={"BTC": Decimal("1"), "ETH": Decimal("2")},
        price_noise_bps=Decimal("0"),
    )
    snap = await ex.get_market_snapshot(["BTC", "ETH"])
    assert "BTC" in snap.quotes and "ETH" in snap.quotes
    assert snap.quotes["BTC"].price == Decimal("100")
    assert snap.quotes["ETH"].price == Decimal("10")


@pytest.mark.asyncio
async def test_mock_exchange_skips_unknown_symbol() -> None:
    ex = MockExchange(
        base_prices={"BTC": Decimal("1")},
        base_volumes={"BTC": Decimal("1")},
        price_noise_bps=Decimal("0"),
    )
    snap = await ex.get_market_snapshot(["BTC", "UNKNOWN"])
    assert "BTC" in snap.quotes
    assert "UNKNOWN" not in snap.quotes
