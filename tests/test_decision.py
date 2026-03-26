"""Decision and domain model tests."""

from __future__ import annotations

from decimal import Decimal

from Engine.models import Action, Decision


def test_decision_frozen() -> None:
    d = Decision(action=Action.BUY, currency="BTC", amount=Decimal("1"), confidence=0.5)
    assert d.action == Action.BUY
    assert d.amount == Decimal("1")
