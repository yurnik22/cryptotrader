"""Mostly HOLD; occasional small trade for demonstration."""

from __future__ import annotations

from decimal import Decimal

from Engine.bots.base_bot import BaseBot
from Engine.models import Action, BotContext, Decision, MarketSnapshot


class PassiveBot(BaseBot):
    async def decide(self, context: BotContext, snapshot: MarketSnapshot) -> Decision:
        sym = str(context.config.get("symbol", "ETH")).upper()
        q = snapshot.quotes.get(sym)
        if q is None:
            return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"), confidence=None)

        cycle_mod = context.config.get("passive_cycle_modulo", 13)
        tick = int(context.cycle_index)
        if cycle_mod and tick % int(cycle_mod) != 0:
            return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"), confidence=0.9)

        usd = context.balances.get("USD", Decimal("0"))
        tiny = Decimal(str(context.config.get("passive_quote_size_usd", "4")))
        if usd < tiny:
            return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"), confidence=0.4)

        qty = (tiny / q.price).quantize(Decimal("0.00000001"))
        if qty <= 0:
            return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"))
        return Decision(action=Action.BUY, currency=sym, amount=qty, confidence=0.25)
