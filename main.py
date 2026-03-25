"""Entry point — paper trading multi-bot runner."""

from __future__ import annotations

import asyncio
import json
import logging
from decimal import Decimal
from pathlib import Path

from Database.db import (
    create_engine_from_url,
    create_session_factory,
    dispose_engine,
    init_db,
    make_url,
)
from Database.repository import Repositories
from Engine.order_executor import OrderExecutor
from Engine.risk_manager import RiskManager
from Engine.trading_agent import TradingAgent
from Exchange.mock_exchange import MockExchange
from Utils.helpers import load_yaml_config, to_decimal
from Utils.logger import configure_logging


async def _seed_bots_if_needed(
    *,
    session_factory,
    repos: Repositories,
    cfg: dict,
) -> None:
    async with session_factory() as session:
        if await repos.bots.has_any_bot(session):
            await session.commit()
            return
        for b in cfg["bots"]:
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
    logging.getLogger("cryptotrader.main").info(
        "seed_complete", extra={"structured": {"bots": len(cfg["bots"])}}
    )


def _build_mock_exchange(cfg: dict) -> MockExchange:
    mx = cfg.get("mock_exchange", {})
    prices_raw = mx.get("prices", {})
    vols_raw = mx.get("volumes", {})
    prices = {str(k).upper(): to_decimal(v) for k, v in prices_raw.items()}
    volumes = {str(k).upper(): to_decimal(v) for k, v in vols_raw.items()}
    noise = to_decimal(mx.get("price_noise_bps", "5"))
    return MockExchange(
        base_prices=prices,
        base_volumes=volumes,
        price_noise_bps=noise,
    )


async def _amain() -> None:
    configure_logging(logging.INFO)
    log = logging.getLogger("cryptotrader.main")
    root = Path(__file__).resolve().parent
    cfg = load_yaml_config(root / "config.yaml")

    db = cfg["database"]
    url = make_url(
        user=str(db["user"]),
        password=str(db["password"]),
        host=str(db["host"]),
        port=int(db["port"]),
        name=str(db["name"]),
    )
    engine = create_engine_from_url(url, echo=False)
    await init_db(engine)
    session_factory = create_session_factory(engine)
    repos = Repositories.default()

    await _seed_bots_if_needed(session_factory=session_factory, repos=repos, cfg=cfg)

    symbols = [str(s).upper() for s in cfg["symbols"]]
    poll = to_decimal(cfg.get("poll_interval", "1.0"))
    risk_cfg = cfg.get("risk", {})
    min_usd = to_decimal(risk_cfg.get("min_order_usd", "1"))
    fee = to_decimal(cfg.get("execution", {}).get("fee_rate", "0"))
    exchange = _build_mock_exchange(cfg)
    risk = RiskManager(min_order_usd=min_usd)
    executor = OrderExecutor(repos, fee_rate=fee)
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
