"""Entry point — async multi-bot paper trading runner."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from Database.db import (
    create_engine_from_url,
    create_session_factory,
    dispose_engine,
    init_db,
    make_url,
)
from Database.repository import Repositories
from Engine.bootstrap import seed_bots_if_needed
from Engine.order_executor import OrderExecutor
from Engine.risk_limits import RiskLimits
from Engine.risk_manager import RiskManager
from Engine.trading_agent import TradingAgent
from Exchange.factory import create_exchange
from Utils.config_loader import load_app_config
from Utils.helpers import to_decimal
from Utils.logger import configure_logging


def _database_url(cfg: dict[str, object]) -> str:
    db = cfg["database"]
    return make_url(
        user=str(db["user"]),
        password=str(db["password"]),
        host=str(db["host"]),
        port=int(db["port"]),
        name=str(db["name"]),
    )


async def _amain() -> None:
    configure_logging(logging.INFO)
    log = logging.getLogger("cryptotrader.main")
    root = Path(__file__).resolve().parent
    cfg = load_app_config(root)

    engine = create_engine_from_url(_database_url(cfg), echo=False)
    await init_db(engine)
    session_factory = create_session_factory(engine)
    repos = Repositories.default()

    await seed_bots_if_needed(session_factory=session_factory, repos=repos, cfg=cfg)

    symbols = [str(s).upper() for s in cfg["symbols"]]
    poll = to_decimal(cfg.get("poll_interval", "1.0"))
    limits = RiskLimits.from_config(cfg.get("risk"))
    risk = RiskManager(limits)
    fee = to_decimal(cfg.get("execution", {}).get("fee_rate", "0"))
    executor = OrderExecutor(repos, fee_rate=fee)
    exchange = create_exchange(cfg)

    agent = TradingAgent(
        session_factory=session_factory,
        repos=repos,
        exchange=exchange,
        risk=risk,
        executor=executor,
        symbols=symbols,
        poll_interval=poll,
    )

    try:
        await agent.run()
    finally:
        await dispose_engine(engine)
        log.info("shutdown_complete")


def main() -> None:
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        logging.getLogger("cryptotrader.main").info("keyboard_interrupt")


if __name__ == "__main__":
    main()
