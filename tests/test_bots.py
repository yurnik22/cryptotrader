"""Smoke tests for strategy bots."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from Engine.bots.aggressive_bot import AggressiveBot
from Engine.bots.passive_bot import PassiveBot
from Engine.bots.smart_bot import SmartBot
from Engine.models import BotContext


def _base_context(config: dict[str, Any]) -> BotContext:
    return BotContext(
        bot_id=1,
        name="x",
        strategy="x",
        allocated_capital=Decimal("100"),
        balances={"USD": Decimal("100")},
        positions=(),
        config=config,
        cycle_index=1,
    )


@pytest.mark.asyncio
async def test_aggressive_bot(btc_eth_snapshot) -> None:
    bot = AggressiveBot(bot_id=1, name="a")
    ctx = _base_context(
        {
            "symbol": "BTC",
            "aggressive_buy_fraction": "0.1",
            "min_order_usd": "1",
        },
    )
    d = await bot.decide(ctx, btc_eth_snapshot)
    assert d.currency.upper() == "BTC"
    assert d.amount >= Decimal("0")


@pytest.mark.asyncio
async def test_passive_bot(btc_eth_snapshot) -> None:
    bot = PassiveBot(bot_id=1, name="p")
    ctx = _base_context(
        {
            "symbol": "ETH",
            "passive_cycle_modulo": 1,
            "passive_quote_size_usd": "4",
        },
    )
    d = await bot.decide(ctx, btc_eth_snapshot)
    assert d.currency.upper() == "ETH"


@pytest.mark.asyncio
async def test_smart_bot(btc_eth_snapshot) -> None:
    bot = SmartBot(bot_id=1, name="s")
    ctx = _base_context(
        {
            "symbol": "BTC",
            "reference_price": "50000",
            "mean_revert_band_bps": "1",
            "smart_order_usd": "10",
        },
    )
    d = await bot.decide(ctx, btc_eth_snapshot)
    assert d.currency.upper() == "BTC"
