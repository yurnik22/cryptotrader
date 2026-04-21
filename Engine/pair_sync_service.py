# Engine/pair_sync_service.py
import logging
from datetime import datetime, timedelta
from typing import List


from Database.repositories import Repositories
from Exchange.factory import get_pairs_fetcher

logger = logging.getLogger(__name__)


class PairSyncService:
    """
    Сервис синхронизации торговых пар с биржей.
    Поддерживает Revolut, Binance и другие биржи через factory.
    """

    def __init__(
        self,
        config: dict,
        session_factory,
        repos: Repositories,
        refresh_interval: timedelta = timedelta(hours=24),
    ):
        self.config = config
        self.session_factory = session_factory
        self.repos = repos
        self.refresh_interval = refresh_interval

        # Определяем провайдера один раз
        self.provider = config.get("api", {}).get("provider", "revolut").lower()

        # Получаем функцию для загрузки пар
        self._fetch_pairs_func = get_pairs_fetcher(self.provider)

        logger.info(f"PairSyncService инициализирован для провайдера: {self.provider}")

    def _is_expired(self, updated_at: datetime) -> bool:
        """Проверяет, устарели ли данные"""
        if not updated_at:
            return True
        return datetime.utcnow() - updated_at > self.refresh_interval

    async def refresh_if_needed(self, *, force: bool = False) -> List[str]:
        """
        Основной метод: обновляет пары только если нужно.
        При force=True — всегда обновляет.
        """
        async with self.session_factory() as session:
            # Получаем текущие данные из БД
            rows = await self.repos.trading_pairs.list_all(session)

            # Если данные свежие и не принудительное обновление — возвращаем из БД
            if rows and not force and not self._is_expired(rows[0].updated_at):
                logger.info(f"Пары свежие ({len(rows)} шт.), обновление пропущено")
                await session.commit()
                return await self.repos.trading_pairs.list_active_symbols(session)

            logger.info(f"Запуск синхронизации пар с {self.provider.upper()}...")

            try:
                # ← Здесь происходит вызов нужной биржи (revolut / binance и т.д.)
                fetched = await self._fetch_pairs_func(config=self.config)
                
                logger.info(f"Получено из API ({self.provider}): {len(fetched)} пар")

            except Exception:
                logger.exception(f"Ошибка при получении пар с {self.provider}")
                await session.commit()
                return await self.repos.trading_pairs.list_active_symbols(session) if rows else []

            if not fetched:
                logger.warning(f"{self.provider.upper()} вернул пустой список пар")
                await session.commit()
                return await self.repos.trading_pairs.list_active_symbols(session) if rows else []

            # Сохраняем в базу
            symbols = await self.repos.trading_pairs.upsert_many(session, fetched)
            await session.commit()

            logger.info(f"pair_sync_success | Провайдер: {self.provider} | Добавлено/обновлено: {len(symbols)} пар")

            return symbols