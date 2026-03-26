"""One-time database seeding for bots, balances, and metrics."""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from Database.repository import Repositories
from Utils.helpers import to_decimal

logger = logging.getLogger("cryptotrader.bootstrap")


async def seed_bots_if_needed(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    repos: Repositories,
    cfg: dict[str, Any],
) -> None:
    """Insert bots from config when the `bots` table is empty."""
    bots_cfg = cfg.get("bots")
    if not isinstance(bots_cfg, list) or not bots_cfg:
        logger.warning("seed_skipped_no_bots_in_config")
        return

    async with session_factory() as session:
        if await repos.bots.has_any_bot(session):
            await session.commit()
            return
        for b in bots_cfg:
            if not isinstance(b, dict):
                continue
            name = str(b["name"])
            strategy = str(b["strategy"])
            cap = to_decimal(b["allocated_capital"])
            cfg_payload = b.get("config", {})
            raw_json = json.dumps(cfg_payload) if cfg_payload else None
            bot = await repos.bots.create_bot(
                session,
                name=name,
                strategy=strategy,
                allocated_capital=cap,
                config_json=raw_json,
            )
            await repos.balances.upsert_balance(session, bot.id, "USD", cap)
            await repos.metrics.ensure_row(session, bot.id)
            await repos.metrics.update_metrics(
                session,
                bot.id,
                equity=cap,
                pnl=Decimal("0"),
                trades_count=0,
            )
        await session.commit()
    logger.info("seed_complete", extra={"structured": {"bots": len(bots_cfg)}})
