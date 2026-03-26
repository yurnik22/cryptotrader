"""Repository layer unit tests (no live DB)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from Database.repository import QuoteRow, Repositories


def test_quote_row_fields() -> None:
    ts = datetime.now(UTC)
    q = QuoteRow(symbol="BTC", price=Decimal("1"), volume=Decimal("2"), ts=ts)
    assert q.symbol == "BTC"
    assert q.price == Decimal("1")


def test_repositories_default_bundle() -> None:
    repos = Repositories.default()
    assert repos.bots is not None
    assert repos.market_data is not None
    assert repos.metrics is not None
