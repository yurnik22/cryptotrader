"""Construct exchange implementations from application config."""

from __future__ import annotations

import logging
import os
from typing import Any

from Exchange.interface import ExchangeInterface
from Exchange.mock_exchange import MockExchange
from Exchange.revolutx_api import RevolutXAdapter
from Utils.helpers import to_decimal

logger = logging.getLogger("cryptotrader.exchange.factory")


def _build_mock_inner(cfg: dict[str, Any]) -> MockExchange:
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


def create_exchange(cfg: dict[str, Any]) -> ExchangeInterface:
    """Return `MockExchange` or `RevolutXAdapter` based on `exchange` key."""
    kind = str(cfg.get("exchange", "mock")).strip().lower()
    if kind == "mock":
        ex = _build_mock_inner(cfg)
        logger.info("exchange_selected", extra={"structured": {"exchange": "mock"}})
        return ex

    if kind in ("revolut", "revolutx"):
        rev = cfg.get("revolut", {}) if isinstance(cfg.get("revolut"), dict) else {}
        use_stub = bool(rev.get("use_stub", True))
        api_base = str(rev.get("api_base", ""))
        api_key = os.getenv("CRYPTOTRADER_REVOLUT_API_KEY")
        stub = _build_mock_inner(cfg) if use_stub else None
        adapter = RevolutXAdapter(
            api_base=api_base,
            api_key=api_key,
            stub_exchange=stub,
        )
        logger.info(
            "exchange_selected",
            extra={"structured": {"exchange": "revolut", "stub": use_stub}},
        )
        return adapter

    msg = f"Unknown exchange backend: {kind!r} (use 'mock' or 'revolut')."
    raise ValueError(msg)
