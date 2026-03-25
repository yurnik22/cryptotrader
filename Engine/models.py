"""Domain models — Decimal for all money and quantities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class MarketQuote:
    price: Decimal
    volume: Decimal
    ts: datetime


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    fetched_at: datetime
    quotes: dict[str, MarketQuote]
    source_meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Decision:
    action: Action
    currency: str
    amount: Decimal
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class PositionView:
    symbol: str
    quantity: Decimal
    avg_price: Decimal


@dataclass(frozen=True, slots=True)
class BotContext:
    bot_id: int
    name: str
    strategy: str
    allocated_capital: Decimal
    balances: dict[str, Decimal]
    positions: tuple[PositionView, ...]
    config: dict[str, Any]
    cycle_index: int = 0
