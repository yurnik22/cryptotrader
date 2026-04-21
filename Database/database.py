# Database/database.py
from .models import Base
from .session import get_engine
import logging

logger = logging.getLogger(__name__)


async def create_tables() -> None:
    """Создаёт таблицы, если их ещё нет"""
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)
        
        logger.info("Таблицы успешно проверены / созданы")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        raise


async def init_database(config: dict) -> None:
    """Полная инициализация базы данных"""
    from .session import get_session_factory

    # Сначала создаём engine и session_factory
    get_session_factory(config)

    # Затем создаём таблицы
    await create_tables()
    logger.info("Инициализация базы данных завершена успешно")