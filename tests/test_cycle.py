"""Equity and quote-row helpers."""

from __future__ import annotations

from decimal import Decimal

from Engine.cycle import equity_for_bot, snapshot_to_quote_rows
from Engine.models import PositionView


def test_equity_for_bot_cash_only(btc_eth_snapshot) -> None:
    eq, pnl = equity_for_bot(
        {"USD": Decimal("100")},
        (),
        btc_eth_snapshot,
        allocated_capital=Decimal("100"),
    )
    assert eq == Decimal("100")
    assert pnl == Decimal("0")


def test_equity_includes_position_mtm(btc_eth_snapshot) -> None:
    pos = (PositionView(symbol="BTC", quantity=Decimal("0.1"), avg_price=Decimal("40000")),)
    eq, _ = equity_for_bot(
        {"USD": Decimal("0")},
        pos,
        btc_eth_snapshot,
        allocated_capital=Decimal("5000"),
    )
    assert eq == Decimal("5000")  # 0.1 * 50000


def test_snapshot_to_quote_rows(btc_eth_snapshot) -> None:
    rows = snapshot_to_quote_rows(btc_eth_snapshot)
    assert len(rows) == 2
    symbols = {r.symbol for r in rows}
    assert symbols == {"BTC", "ETH"}
