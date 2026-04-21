# Database/models.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean
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
