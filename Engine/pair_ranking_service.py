import logging
from decimal import Decimal, InvalidOperation
from statistics import mean
from typing import Any

from Database.repositories import Repositories

logger = logging.getLogger(__name__)


class PairRankingService:
    """Сервис расчёта рангов торговых пар по истории тикеров."""

    def __init__(
        self,
        repos: Repositories,
        history_window: int = 12,
        momentum_window: int = 3,
        drawdown_weight: float = 0.5,
        momentum_weight: float = 0.35,
        spread_weight: float = 0.15,
    ):
        self.repos = repos
        self.history_window = history_window
        self.momentum_window = momentum_window
        self.drawdown_weight = drawdown_weight
        self.momentum_weight = momentum_weight
        self.spread_weight = spread_weight

    async def recalculate(self, session, snapshot_at=None) -> int:
        tickers = await self.repos.tickers.list_all(session)
        pairs = await self.repos.trading_pairs.list_all(session)

        active_tickers = [ticker for ticker in tickers if ticker.active]
        active_pairs_by_symbol = {pair.symbol: pair for pair in pairs if pair.active}

        if not active_tickers or not active_pairs_by_symbol:
            saved = await self.repos.pair_rankings.replace_rankings(session, [], calculated_at=snapshot_at)
            logger.info("pair_ranking_skipped | Нет активных тикеров или торговых пар")
            return saved

        history_by_ticker_id = await self.repos.ticker_history.get_recent_history_by_ticker_ids(
            session,
            [ticker.id for ticker in active_tickers],
            limit_per_ticker=self.history_window,
        )

        rankings = []
        for ticker in active_tickers:
            pair = active_pairs_by_symbol.get(ticker.symbol)
            if not pair:
                continue

            history = history_by_ticker_id.get(ticker.id, [])
            score = self._build_score(ticker, history)
            if score is None:
                continue

            rankings.append(
                {
                    "trading_pair_id": pair.id,
                    "total_score": score["total_score"],
                    "drawdown_score": score["drawdown_score"],
                    "momentum_score": score["momentum_score"],
                    "spread_score": score["spread_score"],
                    "active": True,
                }
            )

        rankings.sort(key=lambda item: item["total_score"], reverse=True)
        saved = await self.repos.pair_rankings.replace_rankings(session, rankings, calculated_at=snapshot_at)
        logger.info("pair_ranking_success | Пересчитано рангов: %s", saved)
        return saved

    def _build_score(self, ticker, history) -> dict[str, float] | None:
        current_price = self._to_float(ticker.last_price)
        bid = self._to_float(ticker.bid)
        ask = self._to_float(ticker.ask)
        mid = self._to_float(ticker.mid)

        if current_price is None or bid is None or ask is None or mid in (None, 0):
            return None

        history_prices = [self._to_float(item.last_price) for item in history]
        history_prices = [price for price in history_prices if price is not None]
        if len(history_prices) < max(self.momentum_window * 2, 2):
            return None

        avg_price = mean(history_prices)
        if avg_price == 0:
            return None

        recent_window = history_prices[: self.momentum_window]
        previous_window = history_prices[self.momentum_window : self.momentum_window * 2]
        if len(previous_window) < self.momentum_window:
            return None

        recent_avg = mean(recent_window)
        previous_avg = mean(previous_window)
        if previous_avg == 0:
            return None

        drawdown_score = (avg_price - current_price) / avg_price
        momentum_score = (recent_avg - previous_avg) / previous_avg
        spread_score = (ask - bid) / mid
        total_score = (
            self.drawdown_weight * drawdown_score
            + self.momentum_weight * momentum_score
            - self.spread_weight * spread_score
        )

        return {
            "total_score": round(total_score, 10),
            "drawdown_score": round(drawdown_score, 10),
            "momentum_score": round(momentum_score, 10),
            "spread_score": round(spread_score, 10),
        }

    def _to_float(self, value: Any) -> float | None:
        try:
            return float(Decimal(str(value)))
        except (InvalidOperation, TypeError, ValueError):
            return None