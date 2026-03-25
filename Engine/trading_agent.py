"""Orchestrates one market snapshot per cycle; bots decide, risk validates, executor applies."""

from __future__ import annotations

import asyncio
import json
import logging
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from Database.models import Bot as BotRow
from Database.repository import QuoteRow, Repositories
from Engine.bot_manager import build_bot
from Engine.models import Action, BotContext, MarketSnapshot, PositionView
from Engine.order_executor import OrderExecutor
from Engine.risk_manager import RiskManager
from Exchange.interface import ExchangeInterface
from Utils.helpers import snapshot_to_payload

logger = logging.getLogger("cryptotrader.agent")


def _equity_for_bot(
    balances: dict[str, Decimal],
    positions: tuple[PositionView, ...],
    snapshot: MarketSnapshot,
    *,
    allocated_capital: Decimal,
) -> tuple[Decimal, Decimal]:
    usd = balances.get("USD", Decimal("0"))
    mtm = Decimal("0")
    for p in positions:
        q = snapshot.quotes.get(p.symbol)
        if q is not None:
            mtm += p.quantity * q.price
    equity = (usd + mtm).quantize(Decimal("0.00000001"))
    pnl = (equity - allocated_capital).quantize(Decimal("0.00000001"))
    return equity, pnl


def _parse_bot_config(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        val = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return val if isinstance(val, dict) else {}


class TradingAgent:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        repos: Repositories,
        exchange: ExchangeInterface,
        risk: RiskManager,
        executor: OrderExecutor,
        symbols: list[str],
        poll_interval: Decimal,
    ) -> None:
        self._session_factory = session_factory
        self._repos = repos
        self._exchange = exchange
        self._risk = risk
        self._executor = executor
        self._symbols = [s.upper() for s in symbols]
        self._poll_interval = poll_interval
        self._cycle = 0

    async def run(self) -> None:
        logger.info("agent_start", extra={"structured": {"poll_interval": str(self._poll_interval)}})
        try:
            while True:
                await self.run_cycle()
                await asyncio.sleep(float(self._poll_interval))
        except asyncio.CancelledError:
            logger.info("agent_cancelled")
            raise

    async def run_cycle(self) -> None:
        self._cycle += 1
        snapshot = await self._exchange.get_market_snapshot(self._symbols)
        payload = snapshot_to_payload(snapshot)
        quote_rows = [
            QuoteRow(symbol=s, price=q.price, volume=q.volume, ts=q.ts)
            for s, q in snapshot.quotes.items()
        ]

        async with self._session_factory() as session:
            try:
                md_id = await self._repos.market_data.save_snapshot(
                    session,
                    fetched_at=snapshot.fetched_at,
                    payload=payload,
                    quotes=quote_rows,
                )
                bots = await self._repos.bots.list_active_bots(session)

                for row in bots:
                    runtime = build_bot(row)
                    balances = await self._repos.balances.get_balances_map(
                        session, row.id
                    )
                    pos_rows = await self._repos.positions.get_positions(session, row.id)
                    positions = tuple(
                        PositionView(
                            symbol=p.symbol,
                            quantity=p.quantity,
                            avg_price=p.avg_price,
                        )
                        for p in pos_rows
                    )
                    cfg = _parse_bot_config(row.config_json)
                    context = BotContext(
                        bot_id=row.id,
                        name=row.name,
                        strategy=row.strategy,
                        allocated_capital=row.allocated_capital,
                        balances=dict(balances),
                        positions=positions,
                        config=cfg,
                        cycle_index=self._cycle,
                    )
                    decision = await runtime.decide(context, snapshot)
                    logger.info(
                        "bot_decision",
                        extra={
                            "structured": {
                                "bot_id": row.id,
                                "bot": row.name,
                                "action": decision.action.value,
                                "symbol": decision.currency,
                                "amount": str(decision.amount),
                            }
                        },
                    )
                    safe = self._risk.validate(decision, context, snapshot)
                    if safe.action in (Action.BUY, Action.SELL) and safe.amount > 0:
                        await self._executor.execute(
                            session,
                            bot_id=row.id,
                            decision=safe,
                            snapshot=snapshot,
                            market_data_id=md_id,
                        )

                # Refresh mark-to-market metrics for all active bots
                refreshed = await self._repos.bots.list_active_bots(session)
                for row in refreshed:
                    balances = await self._repos.balances.get_balances_map(
                        session, row.id
                    )
                    pos_rows = await self._repos.positions.get_positions(session, row.id)
                    positions = tuple(
                        PositionView(
                            symbol=p.symbol,
                            quantity=p.quantity,
                            avg_price=p.avg_price,
                        )
                        for p in pos_rows
                    )
                    equity, pnl = _equity_for_bot(
                        balances,
                        positions,
                        snapshot,
                        allocated_capital=row.allocated_capital,
                    )
                    await self._repos.metrics.ensure_row(session, row.id)
                    await self._repos.metrics.update_metrics(
                        session,
                        row.id,
                        equity=equity,
                        pnl=pnl,
                        trades_count=None,
                    )
                    logger.info(
                        "bot_metrics",
                        extra={
                            "structured": {
                                "bot_id": row.id,
                                "equity": str(equity),
                                "pnl": str(pnl),
                            }
                        },
                    )

                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception("cycle_failed")
                raise
