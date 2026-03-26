"""Applies validated decisions to balances, positions, trades, and metrics."""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from Database.repository import Repositories
from Engine.models import Action, Decision, MarketSnapshot

logger = logging.getLogger("cryptotrader.executor")


class OrderExecutor:
    """Paper execution: DB is source of truth; prices come from the shared snapshot."""

    def __init__(self, repos: Repositories, *, fee_rate: Decimal = Decimal("0")) -> None:
        self._repos = repos
        self._fee_rate = fee_rate

    async def execute(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        decision: Decision,
        snapshot: MarketSnapshot,
        market_data_id: int | None,
    ) -> None:
        if decision.action == Action.BUY:
            await self._execute_buy(session, bot_id, decision, snapshot, market_data_id)
        elif decision.action == Action.SELL:
            await self._execute_sell(session, bot_id, decision, snapshot, market_data_id)

    async def _execute_buy(
        self,
        session: AsyncSession,
        bot_id: int,
        decision: Decision,
        snapshot: MarketSnapshot,
        market_data_id: int | None,
    ) -> None:
        sym = decision.currency.upper()
        quote = snapshot.quotes[sym]
        price = quote.price
        qty = decision.amount.quantize(Decimal("0.00000001"))
        notional = (qty * price).quantize(Decimal("0.00000001"))
        fee = (notional * self._fee_rate).quantize(Decimal("0.00000001"))
        total = notional + fee

        balances = await self._repos.balances.get_balances_map(session, bot_id)
        usd = balances.get("USD", Decimal("0"))
        new_usd = usd - total
        await self._repos.balances.upsert_balance(session, bot_id, "USD", new_usd)
        logger.info(
            "balance_update",
            extra={
                "structured": {
                    "bot_id": bot_id,
                    "asset": "USD",
                    "new_balance": str(new_usd),
                    "reason": "buy",
                }
            },
        )

        pos = await self._repos.positions.get_position(session, bot_id, sym)
        if pos is None:
            await self._repos.positions.upsert_position(session, bot_id, sym, qty, price)
        else:
            old_q = pos.quantity
            old_p = pos.avg_price
            new_q = old_q + qty
            new_avg = ((old_q * old_p + qty * price) / new_q if new_q > 0 else price).quantize(
                Decimal("0.00000001")
            )
            await self._repos.positions.upsert_position(session, bot_id, sym, new_q, new_avg)

        await self._repos.trades.create_trade(
            session,
            bot_id=bot_id,
            side="BUY",
            symbol=sym,
            quantity=qty,
            price=price,
            notional=notional,
            fee=fee,
            market_data_id=market_data_id,
        )
        await self._repos.metrics.increment_trades(session, bot_id)
        logger.info(
            "trade_buy",
            extra={
                "structured": {
                    "bot_id": bot_id,
                    "symbol": sym,
                    "qty": str(qty),
                    "price": str(price),
                    "fee": str(fee),
                }
            },
        )

    async def _execute_sell(
        self,
        session: AsyncSession,
        bot_id: int,
        decision: Decision,
        snapshot: MarketSnapshot,
        market_data_id: int | None,
    ) -> None:
        sym = decision.currency.upper()
        quote = snapshot.quotes[sym]
        price = quote.price
        qty = decision.amount.quantize(Decimal("0.00000001"))
        notional = (qty * price).quantize(Decimal("0.00000001"))
        fee = (notional * self._fee_rate).quantize(Decimal("0.00000001"))
        proceeds = notional - fee

        balances = await self._repos.balances.get_balances_map(session, bot_id)
        usd = balances.get("USD", Decimal("0"))
        new_usd = usd + proceeds
        await self._repos.balances.upsert_balance(session, bot_id, "USD", new_usd)
        logger.info(
            "balance_update",
            extra={
                "structured": {
                    "bot_id": bot_id,
                    "asset": "USD",
                    "new_balance": str(new_usd),
                    "reason": "sell",
                }
            },
        )

        pos = await self._repos.positions.get_position(session, bot_id, sym)
        if pos is None:
            logger.warning(
                "sell_skipped_no_position",
                extra={"structured": {"bot_id": bot_id, "symbol": sym}},
            )
            return
        remaining = (pos.quantity - qty).quantize(Decimal("0.00000001"))
        if remaining <= 0:
            await self._repos.positions.delete_position(session, bot_id, sym)
        else:
            await self._repos.positions.upsert_position(
                session, bot_id, sym, remaining, pos.avg_price
            )

        await self._repos.trades.create_trade(
            session,
            bot_id=bot_id,
            side="SELL",
            symbol=sym,
            quantity=qty,
            price=price,
            notional=notional,
            fee=fee,
            market_data_id=market_data_id,
        )
        await self._repos.metrics.increment_trades(session, bot_id)
        logger.info(
            "trade_sell",
            extra={
                "structured": {
                    "bot_id": bot_id,
                    "symbol": sym,
                    "qty": str(qty),
                    "price": str(price),
                    "fee": str(fee),
                }
            },
        )
