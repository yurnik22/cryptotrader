# Database/repositories.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime

from .models import Symbol, TradingPair

import logging

logger = logging.getLogger(__name__)

class SymbolsRepository:
    """Репозиторий для работы с таблицей symbols"""

    async def list_all(self, session: AsyncSession) -> List[Symbol]:
        """Получить все символы"""
        result = await session.execute(select(Symbol).order_by(Symbol.symbol))
        return list(result.scalars().all())

    async def list_active_names(self, session: AsyncSession) -> List[str]:
        """Получить только активные символы в виде списка строк"""
        result = await session.execute(
            select(Symbol.symbol).where(Symbol.active).order_by(Symbol.symbol)
        )
        return list(result.scalars().all())

    async def upsert_many(self, session: AsyncSession, api_data: list[dict]) -> list[str]:
        if not api_data:
            return []

        api_map = {
            k: v for k, v in api_data.items()
            if v.get("asset_type") == "crypto"
        }

        result = await session.execute(select(Symbol))
        db_rows = result.scalars().all()

        db_map = {row.symbol: row for row in db_rows}

        now = datetime.utcnow()

        for symbol, row in db_map.items():
            if symbol in api_map:
                data = api_map[symbol]

                row.name = data["name"]
                row.active = 1
                row.updated_at = now
            else:
                row.active = 0
                row.updated_at = now

        for symbol, data in api_map.items():
            if symbol not in db_map:
                session.add(
                    Symbol(
                    symbol=symbol,
                    name=data["name"],
                    active=1,
                    created_at=now,
                    updated_at=now
                    )
                )
        
        await session.commit()

        # возвращаем актуальные символы из API
        return sorted(api_map.keys())


class TradingPairsRepository:
    """Репозиторий для работы с таблицей trading_pairs"""

    async def list_all(self, session: AsyncSession) -> List[TradingPair]:
        """Получить все торговые пары"""
        result = await session.execute(select(TradingPair).order_by(TradingPair.symbol))
        return list(result.scalars().all())

    async def list_active_symbols(self, session: AsyncSession) -> List[str]:
        """Получить только активные торговые пары в виде списка строк"""
        result = await session.execute(
            select(TradingPair.symbol)
            .where(TradingPair.active)
            .order_by(TradingPair.symbol)
        )
        return list(result.scalars().all())

    async def upsert_many(self, session: AsyncSession, api_data: list | dict) -> list[str]:
        """
        Обновляет торговые пары из API.

        Поддерживает два формата входных данных:
        - dict: {"BTC/USD": {...}}
        - list[str]: ["BTC/USD", "ETH/EUR"]
        """
        if not api_data:
            return []

        if isinstance(api_data, dict):
            api_map = {
                symbol: data
                for symbol, data in api_data.items()
                if isinstance(symbol, str) and "/" in symbol and isinstance(data, dict)
            }
        else:
            api_map = {
                symbol: {
                    "base": symbol.split("/", 1)[0],
                    "quote": symbol.split("/", 1)[1],
                    "base_step": "0",
                    "quote_step": "0",
                    "min_order_size": "0",
                    "max_order_size": "0",
                    "min_order_size_quote": "0",
                    "status": "active",
                    "active": True,
                }
                for symbol in api_data
                if isinstance(symbol, str) and "/" in symbol
            }

        result = await session.execute(select(TradingPair))
        db_rows = result.scalars().all()
        db_map = {row.symbol: row for row in db_rows}

        now = datetime.utcnow()

        for symbol, row in db_map.items():
            if symbol in api_map:
                data = api_map[symbol]
                base, quote = self._split_symbol(symbol, data)

                row.base = base
                row.quote = quote
                row.base_step = str(data.get("base_step", row.base_step or "0"))
                row.quote_step = str(data.get("quote_step", row.quote_step or "0"))
                row.min_order_size = str(data.get("min_order_size", row.min_order_size or "0"))
                row.max_order_size = str(data.get("max_order_size", row.max_order_size or "0"))
                row.min_order_size_quote = str(
                    data.get("min_order_size_quote", row.min_order_size_quote or "0")
                )
                row.status = str(data.get("status", "active"))
                row.active = bool(data.get("active", row.status == "active"))
                row.updated_at = now
            else:
                row.active = False
                row.updated_at = now

        for symbol, data in api_map.items():
            if symbol not in db_map:
                base, quote = self._split_symbol(symbol, data)
                session.add(
                    TradingPair(
                        symbol=symbol,
                        base=base,
                        quote=quote,
                        base_step=str(data.get("base_step", "0")),
                        quote_step=str(data.get("quote_step", "0")),
                        min_order_size=str(data.get("min_order_size", "0")),
                        max_order_size=str(data.get("max_order_size", "0")),
                        min_order_size_quote=str(data.get("min_order_size_quote", "0")),
                        status=str(data.get("status", "active")),
                        active=bool(data.get("active", data.get("status", "active") == "active")),
                        created_at=now,
                        updated_at=now,
                    )
                )

        await session.commit()
        return sorted(api_map.keys())

    def _split_symbol(self, symbol: str, data: dict) -> tuple[str, str]:
        """Извлекает base/quote из символа или API-данных"""
        base = data.get("base")
        quote = data.get("quote")

        if base and quote:
            return str(base), str(quote)

        if "/" in symbol:
            return tuple(symbol.split("/", 1))

        return symbol, ""

class Repositories:
    """Контейнер для всех репозиториев"""

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.symbols = SymbolsRepository()
        self.trading_pairs = TradingPairsRepository()


# Для удобства можно добавить и другие репозитории позже:
# self.trades = TradesRepository()
# self.orders = OrdersRepository() 
