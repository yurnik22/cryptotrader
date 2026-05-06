# main.py
import asyncio
import logging

from config import load_config, setup_logging
from Database.session import get_session_factory, close_database
from Database.database import init_database
from Database.repositories import Repositories
from Engine.sync_scheduler import ensure_default_sync_tasks, run_pending_sync_tasks
from Engine.trading_cycle import TradingCycle
from Engine.symbol_sync_service import SymbolSyncService
from Engine.pair_sync_service import PairSyncService
from Engine.ticker_sync_service import TickerSyncService
#from Engine.bot import TradingBot


SCHEDULER_SLEEP_SECONDS = 30


async def main():
    try:
        # 1. Загружаем конфиг
        try:
            config = load_config()
        except Exception as e:
            print(f"❌ Ошибка загрузки конфига: {e}")
            return

        # 2. Настраиваем логирование (теперь из config.py)
        setup_logging(config)

        logging.info("Конфигурация успешно загружена")
        logging.info(f"API Provider: {config.get('api', {}).get('provider', 'не указан')}")

        # 3. Инициализируем базу данных (подключение + создание таблиц)
        try:
            await init_database(config)
            logging.info("База данных успешно инициализирована")
        except Exception as e:
            logging.error(f"Ошибка инициализации БД: {e}")
            return

        # 4. Создаём фабрику сессий (уже готова после init_database)
        session_factory = get_session_factory(config)

        # 5. Инициализируем репозитории
        repos = Repositories(session_factory)

        # 6. Создаём сервис синхронизации символов
        symbol_sync = SymbolSyncService(
            config=config,
            session_factory=session_factory,
            repos=repos,
            #refresh_interval=timedelta(hours=24),   # можно изменить
        )

        # 7. Создаём сервис синхронизации пар
        pair_sync = PairSyncService(
            config=config,
            session_factory=session_factory,
            repos=repos,
            #refresh_interval=timedelta(hours=24),   # можно изменить
        )

        ticker_sync = TickerSyncService(
            config=config,
            session_factory=session_factory,
            repos=repos,
        )

        trading_cycle = TradingCycle(
            config=config,
            session_factory=session_factory,
            repos=repos,
        )

        # 8. Инициализируем дефолтные задачи и запускаем scheduler
        await ensure_default_sync_tasks(repos)

        handlers = {
            "sync_symbols": lambda: symbol_sync.refresh_if_needed(force=True),
            "sync_pairs": lambda: pair_sync.refresh_if_needed(force=True),
            "sync_tickers": lambda: ticker_sync.refresh_if_needed(force=True),
        }

        logging.info("Планировщик синхронизации запущен")
        trading_task = asyncio.create_task(trading_cycle.run(), name="trading_cycle")

        try:
            while True:
                await run_pending_sync_tasks(repos, handlers)
                await asyncio.sleep(SCHEDULER_SLEEP_SECONDS)
        except asyncio.CancelledError:
            logging.info("Получен сигнал остановки, завершаем scheduler...")
        finally:
            trading_task.cancel()
            await asyncio.gather(trading_task, return_exceptions=True)

            
    finally:
        # Корректное завершение
        logging.info("Выполняется graceful shutdown...")
        await close_database()
        logging.info("Завершение работы бота")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Программа остановлена пользователем")
