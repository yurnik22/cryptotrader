# Database/models.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Symbol(Base):
    """Модель для хранения торговых символов (BTCUSDT, ETHUSDT и т.д.)"""
    
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    symbol = Column(String(50), unique=True, nullable=False, index=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Symbol(symbol={self.symbol}, active={self.active})>"


class TradingPair(Base):
    """Модель для хранения торговых пар (BTC/USD, ETH/EUR и т.д.)"""
    
    __tablename__ = "trading_pairs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)  # BTC/USD
    base = Column(String(10), nullable=False)  # BTC
    quote = Column(String(10), nullable=False)  # USD
    base_step = Column(String(20), nullable=False)
    quote_step = Column(String(20), nullable=False)
    min_order_size = Column(String(20), nullable=False)
    max_order_size = Column(String(20), nullable=False)
    min_order_size_quote = Column(String(20), nullable=False)
    status = Column(String(10), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<TradingPair(symbol={self.symbol}, base={self.base}, quote={self.quote}, status={self.status})>" 


class Ticker(Base):
    """Модель для хранения актуальных тикеров по торговым парам"""

    __tablename__ = "tickers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    bid = Column(String(30), nullable=False)
    ask = Column(String(30), nullable=False)
    mid = Column(String(30), nullable=False)
    last_price = Column(String(30), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Ticker(symbol={self.symbol}, last_price={self.last_price}, timestamp={self.timestamp})>"


class TickerHistory(Base):
    """Модель для хранения истории snapshot'ов тикеров"""

    __tablename__ = "tickers_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"), nullable=False, index=True)
    bid = Column(String(30), nullable=False)
    ask = Column(String(30), nullable=False)
    mid = Column(String(30), nullable=False)
    last_price = Column(String(30), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return (
            f"<TickerHistory(ticker_id={self.ticker_id}, last_price={self.last_price}, "
            f"timestamp={self.timestamp})>"
        )


class PairRanking(Base):
    """Модель ранга торговой пары по привлекательности для покупки"""

    __tablename__ = "pair_rankings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trading_pair_id = Column(Integer, ForeignKey("trading_pairs.id"), unique=True, nullable=False, index=True)
    total_score = Column(String(30), nullable=False)
    drawdown_score = Column(String(30), nullable=False)
    momentum_score = Column(String(30), nullable=False)
    spread_score = Column(String(30), nullable=False)
    rank_position = Column(Integer, nullable=False, index=True)
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return (
            f"<PairRanking(trading_pair_id={self.trading_pair_id}, total_score={self.total_score}, "
            f"rank_position={self.rank_position})>"
        )


class Position(Base):
    """Модель fake-позиции для последующего перехода к реальной торговле."""

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trading_pair_id = Column(Integer, ForeignKey("trading_pairs.id"), nullable=False, index=True)
    entry_price = Column(String(30), nullable=False)
    exit_price = Column(String(30), nullable=True)
    usd_amount = Column(String(30), nullable=False)
    asset_quantity = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False, index=True)
    source = Column(String(20), nullable=False, default="fake")
    buy_rank_snapshot = Column(String(30), nullable=True)
    pnl_usd = Column(String(30), nullable=True)
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return (
            f"<Position(trading_pair_id={self.trading_pair_id}, status={self.status}, "
            f"usd_amount={self.usd_amount})>"
        )


class SyncTask(Base):
    """Модель расписания задач синхронизации."""

    __tablename__ = "sync_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    service = Column(String(100), unique=True, nullable=False, index=True)
    period = Column(String(100), nullable=False)
    updated_at = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return (
            f"<SyncTask(service={self.service}, period={self.period}, "
            f"updated_at={self.updated_at}, active={self.active})>"
        )
