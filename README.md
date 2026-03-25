# Crypto Trading Multi-Bot System

This project implements a modular cryptocurrency trading system.

## Concept

- Multiple independent trading bots
- Shared market data snapshot
- Independent bot balances
- Paper trading using database
- Future integration with Revolut X API

## Architecture

TradingAgent coordinates bots but does not trade itself.

Bots:
- aggressive
- passive
- smart

Each bot acts as an independent trader.

Market data is fetched once per cycle and shared across bots.