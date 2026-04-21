# Engine/symbol_sync_service.py
import logging
from datetime import datetime, timedelta
from typing import List


from Database.repositories import Repositories
from Exchange.factory import get_symbols_fetcher

logger = logging.getLogger(__name__)


class SymbolSyncService:
    """
    Сервис синхронизации торговых символов с биржей.
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

        self.provider = config.get("api", {}).get("provider", "revolut").lower()
        self._fetch_symbols_func = get_symbols_fetcher(self.provider)

        logger.info(f"SymbolSyncService инициализирован для провайдера: {self.provider}")

    def _is_expired(self, updated_at: datetime) -> bool:
        if not updated_at:
            return True
        return datetime.utcnow() - updated_at > self.refresh_interval

    async def refresh_if_needed(self, *, force: bool = False) -> List[str]:
        """
        Основной метод синхронизации символов.
        """
        async with self.session_factory() as session:
            rows = await self.repos.symbols.list_all(session)

            # Проверка кэша
            if rows and not force and not self._is_expired(rows[0].updated_at):
                logger.info(f"Символы свежие ({len(rows)} шт.), обновление пропущено")
                await session.commit()
                return await self.repos.symbols.list_active_names(session)

            logger.info(f"Запуск синхронизации символов с {self.provider.upper()}...")

            try:
                fetched = await self._fetch_symbols_func(config=self.config)
                logger.info(f"Получено из API ({self.provider}): {len(fetched)} элементов")
            except Exception:
                logger.exception(f"Ошибка при получении символов с {self.provider}")
                await session.commit()
                return await self.repos.symbols.list_active_names(session) if rows else []

            if not fetched:
                logger.warning(f"{self.provider.upper()} вернул пустой результат")
                await session.commit()
                return await self.repos.symbols.list_active_names(session) if rows else []

            # Сохраняем в базу
            names = await self.repos.symbols.upsert_many(session, fetched)
            await session.commit()

            logger.info(f"symbol_sync_success | Провайдер: {self.provider} | "
                       f"Добавлено/обновлено: {len(names)} символов")

            return names