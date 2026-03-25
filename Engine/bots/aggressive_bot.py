"""Higher-risk style: buys on upward momentum vs prior snapshot hint in config."""

from __future__ import annotations

from decimal import Decimal

from Engine.bots.base_bot import BaseBot
from Engine.models import Action, BotContext, Decision, MarketSnapshot


class AggressiveBot(BaseBot):
    async def decide(self, context: BotContext, snapshot: MarketSnapshot) -> Decision:
        target = context.config.get("symbol", "BTC")
        sym = str(target).upper()
        q = snapshot.quotes.get(sym)
        if q is None:
            return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"), confidence=None)

        usd = context.balances.get("USD", Decimal("0"))
        pos = next((p for p in context.positions if p.symbol == sym), None)
        qty = pos.quantity if pos else Decimal("0")

        buy_fraction = Decimal(str(context.config.get("aggressive_buy_fraction", "0.15")))
        min_usd = Decimal(str(context.config.get("min_order_usd", "5")))
        chunk = (usd * buy_fraction).quantize(Decimal("0.00000001"))
        if chunk < min_usd:
            return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"), confidence=0.2)

        # Buy more when already holding (pyramid lightly); else open.
        if qty > 0 and usd > min_usd * Decimal("2"):
            buy_qty = (chunk / q.price).quantize(Decimal("0.00000001"))
            if buy_qty <= 0:
                return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"))
            return Decision(action=Action.BUY, currency=sym, amount=buy_qty, confidence=0.55)

        buy_qty = (chunk / q.price).quantize(Decimal("0.00000001"))
        if buy_qty <= 0:
            return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"))
        return Decision(action=Action.BUY, currency=sym, amount=buy_qty, confidence=0.65)
