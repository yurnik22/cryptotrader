# Web/ws/ws_manager.py
import asyncio
import json
from fastapi import WebSocket

clients = set()


async def register(ws: WebSocket):
    await ws.accept()
    clients.add(ws)


def unregister(ws: WebSocket):
    clients.discard(ws)


async def broadcast(data: dict):
    dead = []

    for ws in clients:
        try:
            await ws.send_text(json.dumps(data))
        except:
            dead.append(ws)

    for d in dead:
        unregister(d)