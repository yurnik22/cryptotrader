"""Trading-cycle helpers — equity, bot config parsing, quote rows."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from Database.repository import QuoteRow
from Engine.models import MarketSnapshot, PositionView


def equity_for_bot(
    balances: dict[str, Decimal],
    positions: tuple[PositionView, ...],
    snapshot: MarketSnapshot,
    *,
    allocated_capital: Decimal,
) -> tuple[Decimal, Decimal]:
    """Return (mark_to_market_equity, pnl_vs_allocated)."""
    usd = balances.get("USD", Decimal("0"))
    mtm = Decimal("0")
    for p in positions:
        q = snapshot.quotes.get(p.symbol)
        if q is not None:
            mtm += p.quantity * q.price
    equity = (usd + mtm).quantize(Decimal("0.00000001"))
    pnl = (equity - allocated_capital).quantize(Decimal("0.00000001"))
    return equity, pnl


def parse_bot_config(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        val = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return val if isinstance(val, dict) else {}


def snapshot_to_quote_rows(snapshot: MarketSnapshot) -> list[QuoteRow]:
    return [
        QuoteRow(symbol=s, price=q.price, volume=q.volume, ts=q.ts)
        for s, q in snapshot.quotes.items()
    ]
