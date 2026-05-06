from __future__ import annotations

import logging
from datetime import datetime
from typing import Awaitable, Callable

from Database.repositories import Repositories

logger = logging.getLogger(__name__)


DEFAULT_SYNC_TASKS = [
    {
        "name": "Синхронизация списка валют",
        "service": "sync_symbols",
        "period": "1d",
        "active": True,
    },
    {
        "name": "Синхронизация списка торговых пар",
        "service": "sync_pairs",
        "period": "1d",
        "active": True,
    },
    {
        "name": "Синхронизация тикеров",
        "service": "sync_tickers",
        "period": "1h",
        "active": True,
    },
]


async def ensure_default_sync_tasks(repos: Repositories) -> None:
    async with repos.session_factory() as session:
        await repos.sync_tasks.ensure_defaults(session, DEFAULT_SYNC_TASKS)


async def run_pending_sync_tasks(
    repos: Repositories,
    handlers: dict[str, Callable[[], Awaitable[list[str]]]],
) -> None:
    async with repos.session_factory() as session:
        tasks = await repos.sync_tasks.list_active(session)

    now = datetime.utcnow()

    for task in tasks:
        if task.service not in handlers:
            logger.warning(
                "Для задачи '%s' не найден обработчик service='%s'",
                task.name,
                task.service,
            )
            continue

        try:
            if not repos.sync_tasks.is_due(task, now=now):
                continue
        except Exception:
            logger.exception(
                "Ошибка при расчете периода для задачи '%s' (period=%s)",
                task.service,
                task.period,
            )
            continue

        logger.info("→ Запускаем задачу '%s' [%s]", task.name, task.period)

        try:
            result = await handlers[task.service]()
            result_count = len(result) if isinstance(result, list) else 0

            async with repos.session_factory() as session:
                await repos.sync_tasks.mark_executed(session, task.id, executed_at=datetime.utcnow())

            logger.info(
                "✓ Задача '%s' выполнена успешно. Обработано элементов: %s",
                task.name,
                result_count,
            )
        except Exception:
            logger.exception("✗ Ошибка выполнения задачи '%s'", task.name)