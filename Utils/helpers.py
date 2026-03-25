"""Pure helpers — config I/O and JSON-safe snapshot payloads."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from Engine.models import MarketSnapshot


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        msg = "config root must be a mapping"
        raise ValueError(msg)
    return data


def to_decimal(value: str | int | float | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        msg = "float is not allowed for monetary paths; use string or int in config"
        raise TypeError(msg)
    return Decimal(str(value))


def utc_now_iso() -> str:
    return datetime.now().isoformat()


def snapshot_to_payload(snapshot: MarketSnapshot) -> dict[str, Any]:
    """Serialize snapshot for `market_data.payload` JSON (decimals as strings)."""
    quotes: dict[str, Any] = {}
    for sym, q in snapshot.quotes.items():
        quotes[sym] = {
            "price": str(q.price),
            "volume": str(q.volume),
            "ts": q.ts.isoformat(),
        }
    return {
        "fetched_at": snapshot.fetched_at.isoformat(),
        "source_meta": snapshot.source_meta,
        "quotes": quotes,
    }
