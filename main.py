# main.py
import asyncio
import logging

from config import load_config, setup_logging
from Database.session import get_session_factory, close_database
from Database.database import init_database
from Database.repositories import Repositories
from Engine.symbol_sync_service import SymbolSyncService
from Engine.pair_sync_service import PairSyncService
#from Engine.bot import TradingBot


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

        # 8. ЗАПУСКАЕМ СИНХРОНИЗАЦИЮ ДО БОТА ===
        logging.info("→ Запускаем синхронизацию торговых символов...")
        try:
            symbols = await symbol_sync.refresh_if_needed(force=True)   # force=True при старте
            logging.info(f"✓ Синхронизация символов завершена. Всего символов: {len(symbols)}")
            if symbols:
                logging.info(f"Первые 10 символов: {symbols[:10]}")
        except Exception:
            logging.exception("✗ Критическая ошибка при синхронизации символов")
            await close_database()
            return

        logging.info("→ Запускаем синхронизацию торговых пар...")
        try:
            pairs = await pair_sync.refresh_if_needed(force=True)   # force=True при старте
            logging.info(f"✓ Синхронизация пар завершена. Всего пар: {len(pairs)}")
            if pairs:
                logging.info(f"Первые 10 пар: {pairs[:10]}")
        except Exception:
            logging.exception("✗ Критическая ошибка при синхронизации пар")
            await close_database()
            return


        # 5. Создаём главный бот
        '''bot = TradingBot(
            config=config,
            session_factory=session_factory,
            repos=repos,
        )'''

        # 6. Запускаем бота
        '''print("🚀 Запуск TradingBot...")
        try:
            await bot.run()
        except KeyboardInterrupt:
            print("\n⛔ Бот остановлен пользователем")
        except Exception as e:
            logging.exception("Критическая ошибка при работе бота")
        finally:
            # Можно добавить graceful shutdown здесь
            print("👋 Завершение работы")'''
            
    finally:
        # Корректное завершение
        logging.info("Выполняется graceful shutdown...")
        await close_database()
        logging.info("Завершение работы бота")


if __name__ == "__main__":
    asyncio.run(main()) 
