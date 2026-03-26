"""Orchestrates one market snapshot per cycle; bots decide, risk validates, executor applies."""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tenacity import stop_after_attempt, wait_exponential
from tenacity.asyncio import AsyncRetrying

from Database.repository import Repositories
from Engine.bot_manager import build_bot
from Engine.cycle import equity_for_bot, parse_bot_config, snapshot_to_quote_rows
from Engine.models import Action, BotContext, PositionView
from Engine.order_executor import OrderExecutor
from Engine.risk_manager import RiskManager
from Exchange.interface import ExchangeInterface
from Utils.helpers import poll_interval_to_sleep_seconds, snapshot_to_payload

logger = logging.getLogger("cryptotrader.agent")


class TradingAgent:
    """Async orchestrator: one exchange snapshot per cycle, shared by all bots."""

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
        cycle_retry_attempts: int = 5,
    ) -> None:
        self._session_factory = session_factory
        self._repos = repos
        self._exchange = exchange
        self._risk = risk
        self._executor = executor
        self._symbols = [s.upper() for s in symbols]
        self._poll_interval = poll_interval
        self._cycle = 0
        self._cycle_retry_attempts = cycle_retry_attempts

    async def run(self) -> None:
        logger.info(
            "agent_start",
            extra={"structured": {"poll_interval": str(self._poll_interval)}},
        )
        try:
            while True:
                self._cycle += 1
                try:
                    async for attempt in AsyncRetrying(
                        stop=stop_after_attempt(self._cycle_retry_attempts),
                        wait=wait_exponential(multiplier=1, min=1, max=45),
                        reraise=True,
                    ):
                        async with attempt:
                            await self._run_cycle()
                except Exception:
                    logger.exception(
                        "cycle_failed_after_retries",
                        extra={
                            "structured": {
                                "cycle": str(self._cycle),
                                "attempts": str(self._cycle_retry_attempts),
                            }
                        },
                    )
                await asyncio.sleep(poll_interval_to_sleep_seconds(self._poll_interval))
        except asyncio.CancelledError:
            logger.info("agent_cancelled")
            raise

    async def _run_cycle(self) -> None:
        """Single attempt of fetch → persist → bots → metrics → commit."""
        snapshot = await self._exchange.get_market_snapshot(self._symbols)
        payload = snapshot_to_payload(snapshot)
        quote_rows = snapshot_to_quote_rows(snapshot)

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
                    balances = await self._repos.balances.get_balances_map(session, row.id)
                    pos_rows = await self._repos.positions.get_positions(session, row.id)
                    positions = tuple(
                        PositionView(
                            symbol=p.symbol,
                            quantity=p.quantity,
                            avg_price=p.avg_price,
                        )
                        for p in pos_rows
                    )
                    mark_equity, _ = equity_for_bot(
                        balances,
                        positions,
                        snapshot,
                        allocated_capital=row.allocated_capital,
                    )
                    self._risk.note_mark_equity(row.id, mark_equity, self._cycle)

                    runtime = build_bot(row)
                    cfg = parse_bot_config(row.config_json)
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
                    safe = self._risk.validate(
                        decision,
                        context,
                        snapshot,
                        mark_equity=mark_equity,
                        cycle_index=self._cycle,
                    )
                    if safe.action in (Action.BUY, Action.SELL) and safe.amount > 0:
                        await self._executor.execute(
                            session,
                            bot_id=row.id,
                            decision=safe,
                            snapshot=snapshot,
                            market_data_id=md_id,
                        )

                refreshed = await self._repos.bots.list_active_bots(session)
                for row in refreshed:
                    balances = await self._repos.balances.get_balances_map(session, row.id)
                    pos_rows = await self._repos.positions.get_positions(session, row.id)
                    positions = tuple(
                        PositionView(
                            symbol=p.symbol,
                            quantity=p.quantity,
                            avg_price=p.avg_price,
                        )
                        for p in pos_rows
                    )
                    equity, pnl = equity_for_bot(
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
