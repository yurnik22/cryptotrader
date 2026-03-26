"""RiskManager behaviour (stateful)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from Engine.models import Action, BotContext, Decision, MarketSnapshot
from Engine.risk_limits import RiskLimits
from Engine.risk_manager import RiskManager


def _ctx(bot_id: int = 1) -> BotContext:
    return BotContext(
        bot_id=bot_id,
        name="t",
        strategy="t",
        allocated_capital=Decimal("100"),
        balances={"USD": Decimal("100")},
        positions=(),
        config={},
        cycle_index=1,
    )


@pytest.fixture
def limits() -> RiskLimits:
    return RiskLimits(
        min_order_usd=Decimal("1"),
        max_position_notional_fraction=Decimal("0.99"),
        max_drawdown_fraction=Decimal("0.5"),
        daily_loss_limit_fraction=Decimal("0.5"),
        circuit_breaker_reject_streak=100,
        circuit_breaker_pause_cycles=10,
    )


def test_hold_passthrough(
    limits: RiskLimits,
    btc_eth_snapshot: MarketSnapshot,
) -> None:
    rm = RiskManager(limits)
    d = Decision(action=Action.HOLD, currency="BTC", amount=Decimal("0"))
    out = rm.validate(
        d,
        _ctx(),
        btc_eth_snapshot,
        mark_equity=Decimal("100"),
        cycle_index=1,
    )
    assert out.action == Action.HOLD


def test_buy_rejected_missing_quote(
    limits: RiskLimits,
    btc_eth_snapshot: MarketSnapshot,
) -> None:
    rm = RiskManager(limits)
    d = Decision(action=Action.BUY, currency="DOGE", amount=Decimal("1"))
    out = rm.validate(
        d,
        _ctx(),
        btc_eth_snapshot,
        mark_equity=Decimal("100"),
        cycle_index=1,
    )
    assert out.action == Action.HOLD


def test_buy_allowed(
    limits: RiskLimits,
    btc_eth_snapshot: MarketSnapshot,
) -> None:
    rm = RiskManager(limits)
    rm.note_mark_equity(1, Decimal("100"), 1)
    d = Decision(action=Action.BUY, currency="BTC", amount=Decimal("0.001"))
    out = rm.validate(
        d,
        _ctx(),
        btc_eth_snapshot,
        mark_equity=Decimal("100"),
        cycle_index=2,
    )
    assert out.action == Action.BUY
