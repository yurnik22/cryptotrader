# Database/repositories.py
from collections import defaultdict
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime
import re

from .models import Symbol, TradingPair, Ticker, TickerHistory, PairRanking, Position, SyncTask

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


class TickersRepository:
    """Репозиторий для работы с таблицей tickers"""

    async def list_all(self, session: AsyncSession) -> List[Ticker]:
        """Получить все тикеры"""
        result = await session.execute(select(Ticker).order_by(Ticker.symbol))
        return list(result.scalars().all())

    async def list_active_symbols(self, session: AsyncSession) -> List[str]:
        """Получить только активные тикеры в виде списка строк"""
        result = await session.execute(
            select(Ticker.symbol)
            .where(Ticker.active)
            .order_by(Ticker.symbol)
        )
        return list(result.scalars().all())

    async def get_ids_by_symbols(self, session: AsyncSession, symbols: list[str]) -> dict[str, int]:
        """Получить соответствие symbol -> ticker.id"""
        if not symbols:
            return {}

        result = await session.execute(
            select(Ticker.symbol, Ticker.id).where(Ticker.symbol.in_(symbols))
        )
        return {symbol: ticker_id for symbol, ticker_id in result.all()}

    async def upsert_many(
        self,
        session: AsyncSession,
        api_data: list[dict],
        snapshot_at: datetime | None = None,
    ) -> list[str]:
        """Массовое обновление тикеров из API"""
        if not api_data:
            return []

        api_map = {
            item["symbol"]: item
            for item in api_data
            if isinstance(item, dict) and item.get("symbol")
        }

        result = await session.execute(select(Ticker))
        db_rows = result.scalars().all()
        db_map = {row.symbol: row for row in db_rows}

        now = datetime.utcnow()
        snapshot_at = snapshot_at or now

        for symbol, row in db_map.items():
            if symbol in api_map:
                data = api_map[symbol]
                row.bid = str(data.get("bid", row.bid))
                row.ask = str(data.get("ask", row.ask))
                row.mid = str(data.get("mid", row.mid))
                row.last_price = str(data.get("last_price", row.last_price))
                row.timestamp = snapshot_at
                row.active = True
                row.updated_at = now
            else:
                row.active = False
                row.updated_at = now

        for symbol, data in api_map.items():
            if symbol not in db_map:
                session.add(
                    Ticker(
                        symbol=symbol,
                        bid=str(data.get("bid", "0")),
                        ask=str(data.get("ask", "0")),
                        mid=str(data.get("mid", "0")),
                        last_price=str(data.get("last_price", "0")),
                        timestamp=snapshot_at,
                        active=True,
                        created_at=now,
                        updated_at=now,
                    )
                )

        await session.commit()
        return sorted(api_map.keys())


class TickerHistoryRepository:
    """Репозиторий для работы с таблицей tickers_history"""

    async def bulk_insert_snapshots(
        self,
        session: AsyncSession,
        api_data: list[dict],
        ticker_ids: dict[str, int],
        snapshot_at: datetime | None = None,
    ) -> int:
        """Массово сохраняет snapshot'ы тикеров в историю"""
        if not api_data or not ticker_ids:
            return 0

        now = datetime.utcnow()
        snapshot_at = snapshot_at or now
        history_rows = []

        for item in api_data:
            if not isinstance(item, dict):
                continue

            symbol = item.get("symbol")
            ticker_id = ticker_ids.get(symbol)
            if not symbol or ticker_id is None:
                continue

            history_rows.append(
                TickerHistory(
                    ticker_id=ticker_id,
                    bid=str(item.get("bid", "0")),
                    ask=str(item.get("ask", "0")),
                    mid=str(item.get("mid", "0")),
                    last_price=str(item.get("last_price", "0")),
                    timestamp=snapshot_at,
                    created_at=now,
                )
            )

        if not history_rows:
            return 0

        session.add_all(history_rows)
        await session.flush()
        return len(history_rows)

    async def get_recent_history_by_ticker_ids(
        self,
        session: AsyncSession,
        ticker_ids: list[int],
        limit_per_ticker: int,
    ) -> dict[int, list[TickerHistory]]:
        """Возвращает последние snapshot'ы по каждому ticker_id"""
        if not ticker_ids or limit_per_ticker <= 0:
            return {}

        result = await session.execute(
            select(TickerHistory)
            .where(TickerHistory.ticker_id.in_(ticker_ids))
            .order_by(TickerHistory.ticker_id, TickerHistory.timestamp.desc(), TickerHistory.id.desc())
        )

        grouped: dict[int, list[TickerHistory]] = defaultdict(list)
        for row in result.scalars().all():
            if len(grouped[row.ticker_id]) < limit_per_ticker:
                grouped[row.ticker_id].append(row)

        return dict(grouped)


class PairRankingsRepository:
    """Репозиторий для работы с таблицей pair_rankings"""

    async def replace_rankings(
        self,
        session: AsyncSession,
        rankings: list[dict],
        calculated_at: datetime | None = None,
    ) -> int:
        """Полностью заменяет актуальный набор рангов"""
        await session.execute(delete(PairRanking))

        if not rankings:
            await session.flush()
            return 0

        calculated_at = calculated_at or datetime.utcnow()
        rows = []

        for index, item in enumerate(rankings, start=1):
            rows.append(
                PairRanking(
                    trading_pair_id=item["trading_pair_id"],
                    total_score=str(item["total_score"]),
                    drawdown_score=str(item["drawdown_score"]),
                    momentum_score=str(item["momentum_score"]),
                    spread_score=str(item["spread_score"]),
                    rank_position=index,
                    calculated_at=calculated_at,
                    active=bool(item.get("active", True)),
                )
            )

        session.add_all(rows)
        await session.flush()
        return len(rows)

    async def list_ranked_active_pairs(self, session: AsyncSession) -> list[PairRanking]:
        result = await session.execute(
            select(PairRanking)
            .where(PairRanking.active)
            .order_by(PairRanking.rank_position.asc(), PairRanking.id.asc())
        )
        return list(result.scalars().all())


class PositionsRepository:
    """Репозиторий для fake-позиций."""

    async def list_open(self, session: AsyncSession) -> list[Position]:
        result = await session.execute(
            select(Position)
            .where(Position.status == "open")
            .order_by(Position.opened_at.asc(), Position.id.asc())
        )
        return list(result.scalars().all())

    async def has_open_position(self, session: AsyncSession, trading_pair_id: int) -> bool:
        result = await session.execute(
            select(Position.id)
            .where(Position.trading_pair_id == trading_pair_id)
            .where(Position.status == "open")
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def sum_open_usd_amount(self, session: AsyncSession) -> float:
        positions = await self.list_open(session)
        total = 0.0
        for position in positions:
            try:
                total += float(position.usd_amount)
            except (TypeError, ValueError):
                continue
        return total

    async def create_fake_buy(
        self,
        session: AsyncSession,
        *,
        trading_pair_id: int,
        entry_price: str,
        usd_amount: str,
        asset_quantity: str,
        buy_rank_snapshot: str | None = None,
    ) -> Position:
        now = datetime.utcnow()
        row = Position(
            trading_pair_id=trading_pair_id,
            entry_price=str(entry_price),
            usd_amount=str(usd_amount),
            asset_quantity=str(asset_quantity),
            status="open",
            source="fake",
            buy_rank_snapshot=str(buy_rank_snapshot) if buy_rank_snapshot is not None else None,
            opened_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        await session.flush()
        return row

    async def close_position(
        self,
        session: AsyncSession,
        *,
        position_id: int,
        exit_price: str,
        pnl_usd: str,
    ) -> Position | None:
        row = await session.get(Position, position_id)
        if not row or row.status != "open":
            return None

        now = datetime.utcnow()
        row.exit_price = str(exit_price)
        row.pnl_usd = str(pnl_usd)
        row.status = "closed"
        row.closed_at = now
        row.updated_at = now
        await session.flush()
        return row


class SyncTasksRepository:
    """Репозиторий для работы с таблицей расписания sync_tasks."""

    PERIOD_PART_RE = re.compile(r"(?P<value>\d+)\s*(?P<unit>[dhms])", re.IGNORECASE)
    PERIOD_MULTIPLIERS = {
        "d": 86400,
        "h": 3600,
        "m": 60,
        "s": 1,
    }

    async def list_active(self, session: AsyncSession) -> List[SyncTask]:
        result = await session.execute(
            select(SyncTask)
            .where(SyncTask.active)
            .order_by(SyncTask.id)
        )
        return list(result.scalars().all())

    async def ensure_defaults(self, session: AsyncSession, tasks: list[dict]) -> None:
        if not tasks:
            return

        result = await session.execute(select(SyncTask))
        existing_rows = result.scalars().all()
        existing_by_service = {row.service: row for row in existing_rows}

        for task in tasks:
            service = task["service"]
            row = existing_by_service.get(service)

            if row:
                row.name = task["name"]
                row.period = task["period"]
                row.active = task.get("active", True)
            else:
                session.add(
                    SyncTask(
                        name=task["name"],
                        service=service,
                        period=task["period"],
                        updated_at=task.get("updated_at"),
                        active=task.get("active", True),
                    )
                )

        await session.commit()

    async def mark_executed(
        self,
        session: AsyncSession,
        task_id: int,
        executed_at: datetime | None = None,
    ) -> None:
        row = await session.get(SyncTask, task_id)
        if not row:
            return

        row.updated_at = executed_at or datetime.utcnow()
        await session.commit()

    def parse_period_to_seconds(self, period: str) -> int:
        if not period or not str(period).strip():
            raise ValueError("Период не может быть пустым")

        total_seconds = 0
        normalized = str(period).strip().lower()

        for match in self.PERIOD_PART_RE.finditer(normalized):
            value = int(match.group("value"))
            unit = match.group("unit").lower()
            total_seconds += value * self.PERIOD_MULTIPLIERS[unit]

        if total_seconds <= 0:
            raise ValueError(f"Некорректный период: {period}")

        return total_seconds

    def is_due(self, task: SyncTask, now: datetime | None = None) -> bool:
        now = now or datetime.utcnow()
        if task.updated_at is None:
            return True

        period_seconds = self.parse_period_to_seconds(task.period)
        elapsed = (now - task.updated_at).total_seconds()
        return elapsed >= period_seconds

class Repositories:
    """Контейнер для всех репозиториев"""

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.symbols = SymbolsRepository()
        self.trading_pairs = TradingPairsRepository()
        self.tickers = TickersRepository()
        self.ticker_history = TickerHistoryRepository()
        self.pair_rankings = PairRankingsRepository()
        self.positions = PositionsRepository()
        self.sync_tasks = SyncTasksRepository()


# Для удобства можно добавить и другие репозитории позже:
# self.trades = TradesRepository()
# self.orders = OrdersRepository() 
