# Database/session.py
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession, AsyncEngine
import logging

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_async_session_factory = None


def get_session_factory(config: dict):
    global _engine, _async_session_factory

    if _async_session_factory is not None:
        return _async_session_factory

    database_url = config.get("database", {}).get("url")
    if not database_url:
        raise ValueError("Не указан database.url в конфиге")

    _engine = create_async_engine(
        database_url,
        echo=config.get("database", {}).get("echo", False),
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=20,
    )

    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info("Database engine успешно создан")
    return _async_session_factory


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Engine ещё не создан. Сначала вызовите get_session_factory()")
    return _engine


async def close_database() -> None:
    """Корректно закрывает соединения с БД при завершении программы"""
    global _engine, _async_session_factory

    if _engine is not None:
        try:
            await _engine.dispose()
            logger.info("Database engine успешно закрыт")
        except Exception as e:
            logger.warning(f"Ошибка при закрытии engine: {e}")
        
        _engine = None
        _async_session_factory = None