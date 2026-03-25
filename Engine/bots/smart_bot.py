"""Naive mean-reversion vs a reference price stored in config (Decimal string)."""

from __future__ import annotations

from decimal import Decimal

from Engine.bots.base_bot import BaseBot
from Engine.models import Action, BotContext, Decision, MarketSnapshot


class SmartBot(BaseBot):
    async def decide(self, context: BotContext, snapshot: MarketSnapshot) -> Decision:
        sym = str(context.config.get("symbol", "BTC")).upper()
        q = snapshot.quotes.get(sym)
        if q is None:
            return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"), confidence=None)

        ref = Decimal(str(context.config.get("reference_price", q.price)))
        band = Decimal(str(context.config.get("mean_revert_band_bps", "25"))) / Decimal("10000")
        low = ref * (Decimal("1") - band)
        high = ref * (Decimal("1") + band)

        trade_usd = Decimal(str(context.config.get("smart_order_usd", "12")))
        usd = context.balances.get("USD", Decimal("0"))
        pos = next((p for p in context.positions if p.symbol == sym), None)
        qty = pos.quantity if pos else Decimal("0")

        if q.price > high and qty > 0:
            sell_qty = (qty / Decimal("4")).quantize(Decimal("0.00000001"))
            if sell_qty > 0:
                return Decision(action=Action.SELL, currency=sym, amount=sell_qty, confidence=0.5)
        if q.price < low and usd >= trade_usd:
            buy_qty = (trade_usd / q.price).quantize(Decimal("0.00000001"))
            if buy_qty > 0:
                return Decision(action=Action.BUY, currency=sym, amount=buy_qty, confidence=0.48)

        return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"), confidence=0.35)
