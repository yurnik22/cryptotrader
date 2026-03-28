# Web/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
from Web.ws.ws_manager import register, unregister, broadcast
from Web.ws.state_stream import state_loop
app = FastAPI()


@app.get("/")
async def root():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await register(ws)

    try:
        while True:
            data = await ws.receive_text()
            await broadcast(f"Client says: {data}")

    except WebSocketDisconnect:
        unregister(ws)

@app.on_event("startup")
async def startup():
    asyncio.create_task(state_loop())