# Engine/ticker_sync_service.py
import logging
from datetime import datetime, timedelta
from typing import List

from Database.repositories import Repositories
from Engine.pair_ranking_service import PairRankingService
from Exchange.factory import get_tickers_fetcher

logger = logging.getLogger(__name__)


class TickerSyncService:
    """Сервис синхронизации тикеров с биржей."""

    def __init__(
        self,
        config: dict,
        session_factory,
        repos: Repositories,
        refresh_interval: timedelta = timedelta(minutes=5),
    ):
        self.config = config
        self.session_factory = session_factory
        self.repos = repos
        self.refresh_interval = refresh_interval
        self.pair_ranking_service = PairRankingService(repos)

        self.provider = config.get("api", {}).get("provider", "revolut").lower()
        self._fetch_tickers_func = get_tickers_fetcher(self.provider)

        logger.info(f"TickerSyncService инициализирован для провайдера: {self.provider}")

    def _is_expired(self, updated_at: datetime) -> bool:
        if not updated_at:
            return True
        return datetime.utcnow() - updated_at > self.refresh_interval

    async def refresh_if_needed(self, *, force: bool = False) -> List[str]:
        async with self.session_factory() as session:
            rows = await self.repos.tickers.list_all(session)

            if rows and not force and not self._is_expired(rows[0].updated_at):
                logger.info(f"Тикеры свежие ({len(rows)} шт.), обновление пропущено")
                await session.commit()
                return await self.repos.tickers.list_active_symbols(session)

            logger.info(f"Запуск синхронизации тикеров с {self.provider.upper()}...")

            try:
                fetched = await self._fetch_tickers_func(config=self.config)
                tickers = fetched.get("data", [])
                snapshot_at = fetched.get("timestamp")
                logger.info(f"Получено из API ({self.provider}): {len(tickers)} тикеров")
            except Exception:
                logger.exception(f"Ошибка при получении тикеров с {self.provider}")
                await session.commit()
                return await self.repos.tickers.list_active_symbols(session) if rows else []

            if not tickers:
                logger.warning(f"{self.provider.upper()} вернул пустой список тикеров")
                await session.commit()
                return await self.repos.tickers.list_active_symbols(session) if rows else []

            symbols = await self.repos.tickers.upsert_many(session, tickers, snapshot_at=snapshot_at)
            ticker_ids = await self.repos.tickers.get_ids_by_symbols(session, symbols)
            saved_history_count = await self.repos.ticker_history.bulk_insert_snapshots(
                session,
                tickers,
                ticker_ids,
                snapshot_at=snapshot_at,
            )
            saved_rankings_count = await self.pair_ranking_service.recalculate(
                session,
                snapshot_at=snapshot_at,
            )
            await session.commit()

            logger.info(
                f"ticker_sync_success | Провайдер: {self.provider} | Добавлено/обновлено: {len(symbols)} тикеров | "
                f"Сохранено в историю: {saved_history_count} snapshot'ов | "
                f"Пересчитано рангов: {saved_rankings_count}"
            )
            return symbols