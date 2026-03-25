"""Structured logging setup."""

from __future__ import annotations

import logging
import sys
from typing import Any


class KeyValueFormatter(logging.Formatter):
    """Emit human-readable lines with stable key=value pairs for agents/bots/trades."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extra = getattr(record, "structured", None)
        if not extra:
            return base
        parts = [base]
        for k, v in sorted(extra.items()):
            parts.append(f"{k}={v}")
        return " ".join(parts)


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        KeyValueFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root.handlers.clear()
    root.addHandler(handler)


def log_extra(**kwargs: Any) -> dict[str, Any]:
    """Attach to LogRecord via logger.log(..., extra={"structured": log_extra(...)})"""
    out: dict[str, Any] = {}
    for k, v in kwargs.items():
        if v is None:
            continue
        out[str(k)] = v
    return out
