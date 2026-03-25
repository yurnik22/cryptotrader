"""Repository protocols and SQLAlchemy implementations — no raw SQL outside this module."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol, Sequence, Self

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from Database.models import Balance, Bot, BotMetric, MarketData, MarketQuote, Position, Trade


@dataclass(frozen=True, slots=True)
class QuoteRow:
    symbol: str
    price: Decimal
    volume: Decimal
    ts: datetime


class BotRepositoryProtocol(Protocol):
    async def has_any_bot(self, session: AsyncSession) -> bool: ...
    async def list_active_bots(self, session: AsyncSession) -> list[Bot]: ...
    async def get_bot_by_id(self, session: AsyncSession, bot_id: int) -> Bot | None: ...
    async def get_bot_by_name(self, session: AsyncSession, name: str) -> Bot | None: ...
    async def create_bot(
        self,
        session: AsyncSession,
        *,
        name: str,
        strategy: str,
        allocated_capital: Decimal,
        config_json: str | None,
    ) -> Bot: ...


class BalanceRepositoryProtocol(Protocol):
    async def get_balances_map(self, session: AsyncSession, bot_id: int) -> dict[str, Decimal]: ...
    async def upsert_balance(
        self,
        session: AsyncSession,
        bot_id: int,
        asset: str,
        amount: Decimal,
    ) -> Balance: ...


class PositionRepositoryProtocol(Protocol):
    async def get_positions(self, session: AsyncSession, bot_id: int) -> list[Position]: ...
    async def get_position(
        self, session: AsyncSession, bot_id: int, symbol: str
    ) -> Position | None: ...
    async def upsert_position(
        self,
        session: AsyncSession,
        bot_id: int,
        symbol: str,
        quantity: Decimal,
        avg_price: Decimal,
    ) -> Position: ...


class TradeRepositoryProtocol(Protocol):
    async def create_trade(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        side: str,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        notional: Decimal,
        fee: Decimal,
        market_data_id: int | None,
    ) -> Trade: ...


class MarketDataRepositoryProtocol(Protocol):
    async def save_snapshot(
        self,
        session: AsyncSession,
        *,
        fetched_at: datetime,
        payload: dict[str, Any],
        quotes: Sequence[QuoteRow],
    ) -> int: ...


class BotMetricsRepositoryProtocol(Protocol):
    async def ensure_row(self, session: AsyncSession, bot_id: int) -> BotMetric: ...
    async def update_metrics(
        self,
        session: AsyncSession,
        bot_id: int,
        *,
        equity: Decimal,
        pnl: Decimal,
        trades_count: int | None,
    ) -> None: ...
    async def increment_trades(self, session: AsyncSession, bot_id: int) -> None: ...


class SqlAlchemyBotRepository:
    async def has_any_bot(self, session: AsyncSession) -> bool:
        res = await session.execute(select(Bot.id).limit(1))
        return res.scalar_one_or_none() is not None

    async def list_active_bots(self, session: AsyncSession) -> list[Bot]:
        res = await session.execute(
            select(Bot)
            .where(Bot.is_active.is_(True))
            .options(selectinload(Bot.balances), selectinload(Bot.positions))
        )
        return list(res.scalars().unique().all())

    async def get_bot_by_id(self, session: AsyncSession, bot_id: int) -> Bot | None:
        res = await session.execute(select(Bot).where(Bot.id == bot_id))
        return res.scalar_one_or_none()

    async def get_bot_by_name(self, session: AsyncSession, name: str) -> Bot | None:
        res = await session.execute(select(Bot).where(Bot.name == name))
        return res.scalar_one_or_none()

    async def create_bot(
        self,
        session: AsyncSession,
        *,
        name: str,
        strategy: str,
        allocated_capital: Decimal,
        config_json: str | None,
    ) -> Bot:
        bot = Bot(
            name=name,
            strategy=strategy,
            is_active=True,
            allocated_capital=allocated_capital,
            config_json=config_json,
        )
        session.add(bot)
        await session.flush()
        return bot


class SqlAlchemyBalanceRepository:
    async def get_balances_map(self, session: AsyncSession, bot_id: int) -> dict[str, Decimal]:
        res = await session.execute(select(Balance).where(Balance.bot_id == bot_id))
        rows = res.scalars().all()
        return {b.asset: b.amount for b in rows}

    async def upsert_balance(
        self,
        session: AsyncSession,
        bot_id: int,
        asset: str,
        amount: Decimal,
    ) -> Balance:
        res = await session.execute(
            select(Balance).where(Balance.bot_id == bot_id, Balance.asset == asset)
        )
        row = res.scalar_one_or_none()
        if row is None:
            row = Balance(bot_id=bot_id, asset=asset, amount=amount)
            session.add(row)
        else:
            row.amount = amount
        await session.flush()
        return row


class SqlAlchemyPositionRepository:
    async def get_positions(self, session: AsyncSession, bot_id: int) -> list[Position]:
        res = await session.execute(select(Position).where(Position.bot_id == bot_id))
        return list(res.scalars().all())

    async def get_position(
        self, session: AsyncSession, bot_id: int, symbol: str
    ) -> Position | None:
        res = await session.execute(
            select(Position).where(Position.bot_id == bot_id, Position.symbol == symbol)
        )
        return res.scalar_one_or_none()

    async def upsert_position(
        self,
        session: AsyncSession,
        bot_id: int,
        symbol: str,
        quantity: Decimal,
        avg_price: Decimal,
    ) -> Position:
        res = await session.execute(
            select(Position).where(Position.bot_id == bot_id, Position.symbol == symbol)
        )
        row = res.scalar_one_or_none()
        if row is None:
            row = Position(
                bot_id=bot_id,
                symbol=symbol,
                quantity=quantity,
                avg_price=avg_price,
            )
            session.add(row)
        else:
            row.quantity = quantity
            row.avg_price = avg_price
        await session.flush()
        return row

    async def delete_position(
        self, session: AsyncSession, bot_id: int, symbol: str
    ) -> None:
        await session.execute(
            delete(Position).where(Position.bot_id == bot_id, Position.symbol == symbol)
        )


class SqlAlchemyTradeRepository:
    async def create_trade(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        side: str,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        notional: Decimal,
        fee: Decimal,
        market_data_id: int | None,
    ) -> Trade:
        t = Trade(
            bot_id=bot_id,
            side=side,
            symbol=symbol,
            quantity=quantity,
            price=price,
            notional=notional,
            fee=fee,
            market_data_id=market_data_id,
        )
        session.add(t)
        await session.flush()
        return t


class SqlAlchemyMarketDataRepository:
    async def save_snapshot(
        self,
        session: AsyncSession,
        *,
        fetched_at: datetime,
        payload: dict[str, Any],
        quotes: Sequence[QuoteRow],
    ) -> int:
        md = MarketData(fetched_at=fetched_at, payload=payload)
        session.add(md)
        await session.flush()
        for q in quotes:
            session.add(
                MarketQuote(
                    market_data_id=md.id,
                    symbol=q.symbol,
                    price=q.price,
                    volume=q.volume,
                    ts=q.ts,
                )
            )
        await session.flush()
        return md.id


class SqlAlchemyBotMetricsRepository:
    async def ensure_row(self, session: AsyncSession, bot_id: int) -> BotMetric:
        res = await session.execute(select(BotMetric).where(BotMetric.bot_id == bot_id))
        row = res.scalar_one_or_none()
        if row is None:
            row = BotMetric(
                bot_id=bot_id,
                equity=Decimal("0"),
                pnl=Decimal("0"),
                trades_count=0,
            )
            session.add(row)
            await session.flush()
        return row

    async def update_metrics(
        self,
        session: AsyncSession,
        bot_id: int,
        *,
        equity: Decimal,
        pnl: Decimal,
        trades_count: int | None,
    ) -> None:
        values: dict[str, Any] = {"equity": equity, "pnl": pnl}
        if trades_count is not None:
            values["trades_count"] = trades_count
        await session.execute(update(BotMetric).where(BotMetric.bot_id == bot_id).values(**values))

    async def increment_trades(self, session: AsyncSession, bot_id: int) -> None:
        m = await self.ensure_row(session, bot_id)
        m.trades_count = int(m.trades_count) + 1
        await session.flush()


@dataclass(slots=True)
class Repositories:
    bots: SqlAlchemyBotRepository
    balances: SqlAlchemyBalanceRepository
    positions: SqlAlchemyPositionRepository
    trades: SqlAlchemyTradeRepository
    market_data: SqlAlchemyMarketDataRepository
    metrics: SqlAlchemyBotMetricsRepository

    @classmethod
    def default(cls) -> Self:
        return cls(
            bots=SqlAlchemyBotRepository(),
            balances=SqlAlchemyBalanceRepository(),
            positions=SqlAlchemyPositionRepository(),
            trades=SqlAlchemyTradeRepository(),
            market_data=SqlAlchemyMarketDataRepository(),
            metrics=SqlAlchemyBotMetricsRepository(),
        )
