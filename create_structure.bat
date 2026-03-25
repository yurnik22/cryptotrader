@echo off
echo Creating trading-agent project structure...

REM === ROOT FILES ===
type nul > main.py
type nul > config.yaml
type nul > README.md

REM === ENGINE ===
mkdir Engine
type nul > Engine\trading_agent.py
type nul > Engine\bot_manager.py
type nul > Engine\order_executor.py
type nul > Engine\risk_manager.py
type nul > Engine\models.py

REM === BOTS ===
mkdir Engine\bots
type nul > Engine\bots\base_bot.py
type nul > Engine\bots\aggressive_bot.py
type nul > Engine\bots\passive_bot.py
type nul > Engine\bots\smart_bot.py

REM === EXCHANGE ===
mkdir Exchange
type nul > Exchange\mock_exchange.py
type nul > Exchange\revolutx_api.py

REM === DATABASE ===
mkdir Database
type nul > Database\db.py
type nul > Database\models.py
type nul > Database\repository.py

REM === UTILS ===
mkdir Utils
type nul > Utils\logger.py
type nul > Utils\helpers.py

echo Project structure created successfully!
pause