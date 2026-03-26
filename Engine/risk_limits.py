"""Typed risk limits loaded from configuration (Decimal-safe)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from Utils.helpers import to_decimal


@dataclass(frozen=True, slots=True)
class RiskLimits:
    min_order_usd: Decimal
    max_position_notional_fraction: Decimal
    max_drawdown_fraction: Decimal
    daily_loss_limit_fraction: Decimal
    circuit_breaker_reject_streak: int
    circuit_breaker_pause_cycles: int

    @classmethod
    def from_config(cls, risk_cfg: dict[str, Any] | None) -> RiskLimits:
        r = risk_cfg or {}
        return cls(
            min_order_usd=to_decimal(r.get("min_order_usd", "1")),
            max_position_notional_fraction=to_decimal(
                r.get("max_position_notional_fraction", "0.99")
            ),
            max_drawdown_fraction=to_decimal(r.get("max_drawdown_fraction", "0.99")),
            daily_loss_limit_fraction=to_decimal(r.get("daily_loss_limit_fraction", "0.99")),
            circuit_breaker_reject_streak=int(
                to_decimal(r.get("circuit_breaker_reject_streak", "1000000"))
            ),
            circuit_breaker_pause_cycles=max(
                1,
                int(to_decimal(r.get("circuit_breaker_pause_cycles", "10"))),
            ),
        )
