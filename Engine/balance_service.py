import logging
from decimal import Decimal, InvalidOperation

from Exchange.factory import get_balance_fetcher

logger = logging.getLogger(__name__)


class BalanceService:
    """Сервис получения реального USD-баланса у провайдера."""

    def __init__(self, config: dict):
        self.config = config
        self.provider = config.get("api", {}).get("provider", "revolut").lower()
        self._fetch_balances = get_balance_fetcher(self.provider)

    async def get_usd_balance(self) -> float:
        balances = await self._fetch_balances(config=self.config)
        for item in balances:
            if not isinstance(item, dict):
                continue
            if str(item.get("currency", "")).upper() != "USD":
                continue
            return self._to_float(item.get("available"))

        logger.warning("USD баланс не найден в ответе провайдера, возвращаю 0")
        return 0.0

    def _to_float(self, value) -> float:
        try:
            return float(Decimal(str(value)))
        except (InvalidOperation, TypeError, ValueError):
            return 0.0