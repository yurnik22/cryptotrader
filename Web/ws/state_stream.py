import asyncio
import random
from Web.ws.ws_manager import broadcast


portfolio_value = 10000


async def state_loop():
    global portfolio_value

    while True:
        # fake pnl movement
        portfolio_value += random.uniform(-20, 30)

        state = {
            "portfolio": {
                "value": round(portfolio_value, 2),
                "pnl": round(random.uniform(-3, 5), 2),
            },
            "bots": [
                {
                    "name": "BTC Trend",
                    "status": "RUNNING",
                    "pnl": round(random.uniform(10, 200), 2),
                },
                {
                    "name": "ETH Scalper",
                    "status": "RUNNING",
                    "pnl": round(random.uniform(-20, 80), 2),
                },
            ],
        }

        await broadcast(state)
        await asyncio.sleep(1)