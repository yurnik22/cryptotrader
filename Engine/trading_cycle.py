import asyncio
import logging
from decimal import Decimal, InvalidOperation

from Database.models import PairRanking, Position, Ticker, TradingPair
from Database.repositories import Repositories
from Engine.balance_service import BalanceService
from Engine.entry_decision_service import EntryDecisionService
from Engine.exit_decision_service import ExitDecisionService

logger = logging.getLogger(__name__)


class TradingCycle:
    """Основной цикл fake-trading на основе реального баланса и рангов."""

    def __init__(self, config: dict, session_factory, repos: Repositories):
        self.config = config
        self.session_factory = session_factory
        self.repos = repos

        trading_cfg = config.setdefault("trading", {})
        self.enabled = bool(trading_cfg.get("enabled", True))
        self.stop_loss_pct = float(trading_cfg.get("stop_loss_pct", 0.01))
        self.min_buy_score = float(trading_cfg.get("min_buy_score", 0.0))
        self.min_free_usd = float(trading_cfg.get("min_free_usd", 1.0))
        self.position_size_usd = float(trading_cfg.get("position_size_usd", 10.0))
        self.loop_interval_seconds = int(trading_cfg.get("loop_interval_seconds", 30))

        self.balance_service = BalanceService(config)
        self.entry_decision_service = EntryDecisionService(min_buy_score=self.min_buy_score)
        self.exit_decision_service = ExitDecisionService(stop_loss_pct=self.stop_loss_pct)

    async def run(self) -> None:
        if not self.enabled:
            logger.info("TradingCycle отключён в конфиге")
            return

        logger.info("TradingCycle запущен")
        while True:
            try:
                await self.run_once()
                await asyncio.sleep(self.loop_interval_seconds)
            except asyncio.CancelledError:
                logger.info("TradingCycle остановлен")
                raise
            except Exception:
                logger.exception("Ошибка в TradingCycle")
                await asyncio.sleep(self.loop_interval_seconds)

    async def run_once(self) -> None:
        real_usd_balance = await self.balance_service.get_usd_balance()

        async with self.session_factory() as session:
            open_positions = await self.repos.positions.list_open(session)
            reserved_usd = await self.repos.positions.sum_open_usd_amount(session)
            free_usd = max(real_usd_balance - reserved_usd, 0.0)

            logger.info(
                "trading_cycle_balance | real_usd=%.8f | reserved_usd=%.8f | free_usd=%.8f",
                real_usd_balance,
                reserved_usd,
                free_usd,
            )

            await self._process_entries(session, free_usd)
            await self._process_exits(session, open_positions)
            await session.commit()

    async def _process_entries(self, session, free_usd: float) -> None:
        if free_usd < self.min_free_usd:
            return

        rankings = await self.repos.pair_rankings.list_ranked_active_pairs(session)
        if not rankings:
            return

        remaining_free_usd = free_usd
        for ranking in rankings:
            if remaining_free_usd < self.min_free_usd:
                break

            if not self.entry_decision_service.should_buy(ranking, remaining_free_usd, self.min_free_usd):
                continue

            has_open = await self.repos.positions.has_open_position(session, ranking.trading_pair_id)
            if has_open:
                continue

            pair = await session.get(TradingPair, ranking.trading_pair_id)
            if not pair or not pair.active:
                continue

            ticker = await self._get_ticker_by_symbol(session, pair.symbol)
            if not ticker:
                continue

            entry_price = self._to_float(ticker.last_price)
            if entry_price <= 0:
                continue

            usd_amount = min(remaining_free_usd, self.position_size_usd)
            if usd_amount < self.min_free_usd:
                continue

            asset_quantity = usd_amount / entry_price
            await self.repos.positions.create_fake_buy(
                session,
                trading_pair_id=pair.id,
                entry_price=str(entry_price),
                usd_amount=str(round(usd_amount, 10)),
                asset_quantity=str(round(asset_quantity, 10)),
                buy_rank_snapshot=str(ranking.total_score),
            )
            remaining_free_usd -= usd_amount
            logger.info(
                "fake_buy_created | symbol=%s | usd_amount=%.8f | entry_price=%.8f | rank=%s",
                pair.symbol,
                usd_amount,
                entry_price,
                ranking.total_score,
            )

    async def _process_exits(self, session, open_positions: list[Position]) -> None:
        if not open_positions:
            return

        for position in open_positions:
            pair = await session.get(TradingPair, position.trading_pair_id)
            if not pair:
                continue

            ticker = await self._get_ticker_by_symbol(session, pair.symbol)
            ranking = await self._get_ranking_by_pair_id(session, pair.id)
            if not ticker or not ranking:
                continue

            entry_price = self._to_float(position.entry_price)
            current_price = self._to_float(ticker.last_price)
            asset_quantity = self._to_float(position.asset_quantity)
            momentum_score = self._to_float(ranking.momentum_score)

            if entry_price <= 0 or current_price <= 0 or asset_quantity <= 0:
                continue

            pnl_pct = (current_price - entry_price) / entry_price
            pnl_usd = (current_price - entry_price) * asset_quantity

            if not self.exit_decision_service.should_sell(pnl_pct=pnl_pct, momentum_score=momentum_score):
                continue

            await self.repos.positions.close_position(
                session,
                position_id=position.id,
                exit_price=str(current_price),
                pnl_usd=str(round(pnl_usd, 10)),
            )
            logger.info(
                "fake_sell_created | symbol=%s | exit_price=%.8f | pnl_pct=%.6f | pnl_usd=%.8f",
                pair.symbol,
                current_price,
                pnl_pct,
                pnl_usd,
            )

    async def _get_ticker_by_symbol(self, session, symbol: str) -> Ticker | None:
        tickers = await self.repos.tickers.list_all(session)
        for ticker in tickers:
            if ticker.symbol == symbol and ticker.active:
                return ticker
        return None

    async def _get_ranking_by_pair_id(self, session, trading_pair_id: int) -> PairRanking | None:
        rankings = await self.repos.pair_rankings.list_ranked_active_pairs(session)
        for ranking in rankings:
            if ranking.trading_pair_id == trading_pair_id:
                return ranking
        return None

    def _to_float(self, value) -> float:
        try:
            return float(Decimal(str(value)))
        except (InvalidOperation, TypeError, ValueError):
            return 0.0
