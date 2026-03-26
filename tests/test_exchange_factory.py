"""Exchange factory wiring."""

from __future__ import annotations

from Exchange.factory import create_exchange


def test_create_exchange_mock() -> None:
    cfg = {
        "exchange": "mock",
        "mock_exchange": {
            "prices": {"BTC": "100"},
            "volumes": {"BTC": "1"},
            "price_noise_bps": "0",
        },
    }
    ex = create_exchange(cfg)
    assert ex is not None


def test_create_exchange_revolut_stub() -> None:
    cfg = {
        "exchange": "revolut",
        "mock_exchange": {
            "prices": {"BTC": "100"},
            "volumes": {"BTC": "1"},
            "price_noise_bps": "0",
        },
        "revolut": {"use_stub": True, "api_base": "https://example.com"},
    }
    ex = create_exchange(cfg)
    assert ex is not None
