# Web/main.py
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from Web.api import portfolio, bot_control
from Web.ws import portfolio_ws

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # или список фронтов
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API
app.include_router(portfolio.router, prefix="/api")
app.include_router(bot_control.router, prefix="/api")

# WebSocket
@app.websocket("/ws/portfolio")
async def ws_portfolio(ws: WebSocket):
    await portfolio_ws.connect(ws)
    try:
        while True:
            # если клиент шлёт сообщения (например, команды)
            data = await ws.receive_text()
            print("Message from frontend:", data)
    except:
        await portfolio_ws.disconnect(ws)