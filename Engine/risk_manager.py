"""Pre-trade validation — Decimal-only monetary checks."""

from __future__ import annotations

import logging
from decimal import Decimal

from Engine.models import Action, BotContext, Decision, MarketSnapshot

logger = logging.getLogger("cryptotrader.risk")


class RiskManager:
    def __init__(self, *, min_order_usd: Decimal = Decimal("1")) -> None:
        self._min_order_usd = min_order_usd

    def validate(
        self,
        decision: Decision,
        context: BotContext,
        snapshot: MarketSnapshot,
    ) -> Decision:
        if decision.action == Action.HOLD:
            return decision

        sym = decision.currency.upper()
        quote = snapshot.quotes.get(sym)
        if quote is None:
            logger.info(
                "risk_reject_missing_quote",
                extra={
                    "structured": {
                        "bot_id": context.bot_id,
                        "symbol": sym,
                        "reason": "no_quote",
                    }
                },
            )
            return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"))

        if decision.amount <= 0:
            return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"))

        if decision.action == Action.BUY:
            notional = (decision.amount * quote.price).quantize(Decimal("0.00000001"))
            usd = context.balances.get("USD", Decimal("0"))
            if usd < notional:
                logger.info(
                    "risk_reject_insufficient_usd",
                    extra={
                        "structured": {
                            "bot_id": context.bot_id,
                            "need": str(notional),
                            "have": str(usd),
                        }
                    },
                )
                return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"))
            if notional < self._min_order_usd:
                return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"))

        if decision.action == Action.SELL:
            pos = next((p for p in context.positions if p.symbol == sym), None)
            if pos is None or pos.quantity < decision.amount:
                logger.info(
                    "risk_reject_insufficient_position",
                    extra={
                        "structured": {
                            "bot_id": context.bot_id,
                            "symbol": sym,
                            "want": str(decision.amount),
                            "have": str(pos.quantity if pos else Decimal("0")),
                        }
                    },
                )
                return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"))
            if (decision.amount * quote.price) < self._min_order_usd:
                return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"))

        return decision
