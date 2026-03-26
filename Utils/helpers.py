"""Pure helpers — JSON-safe payloads and Decimal parsing."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from Engine.models import MarketSnapshot


def to_decimal(value: str | int | float | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        msg = "float is not allowed for monetary paths; use string or int in config"
        raise TypeError(msg)
    return Decimal(str(value))


def utc_now_iso() -> str:
    return datetime.now().isoformat()


def poll_interval_to_sleep_seconds(interval: Decimal) -> float:
    """Convert poll interval to seconds for `asyncio.sleep` (I/O only, not pricing)."""
    return float(interval)


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
