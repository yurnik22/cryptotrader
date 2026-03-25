"""Async SQLAlchemy engine, session factory, and schema initialization."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from Database.models import Base

if TYPE_CHECKING:
    pass


def make_url(
    user: str,
    password: str,
    host: str,
    port: int,
    database: str,
) -> str:
    return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{database}"


def create_engine_from_url(url: str, *, echo: bool = False) -> AsyncEngine:
    return create_async_engine(url, echo=echo)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine(engine: AsyncEngine) -> None:
    await engine.dispose()
