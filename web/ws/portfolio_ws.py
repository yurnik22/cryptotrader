# Web/ws/portfolio_ws.py
from fastapi import WebSocket
import json

clients = []

async def connect(ws: WebSocket):
    await ws.accept()
    clients.append(ws)

async def disconnect(ws: WebSocket):
    clients.remove(ws)
    await ws.close()

async def broadcast(data: dict):
    for ws in clients:
        try:
            await ws.send_text(json.dumps(data))
        except:
            await disconnect(ws)