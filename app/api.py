# app/api.py
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path

from .config import settings
from . import db
from .ws_manager import WebSocketManager

def create_app(ws_mgr: WebSocketManager) -> FastAPI:
    app = FastAPI()

    # --- UI (yksinkertainen) ---
    @app.get("/")
    def root():
        # ohjataan suoraan simple UI:hin
        return HTMLResponse(Path(__file__).with_suffix("").parent.joinpath("templates", "simple_ui.html").read_text(encoding="utf-8"))

    @app.get("/simple")
    def simple_ui():
        return root()

    # --- API: aluskatalogi (nimeä/MMSI:tä varten) ---
    @app.get("/api/vessels")
    def api_vessels(q: str | None = Query(default=None, description="FILTTERI nimi tai MMSI")):
        rows = db.query_vessels(q=q, limit=2000)
        return JSONResponse([{"mmsi": r[0], "name": r[1]} for r in rows])

    # --- API: 3h historia 15 min resoluutiolla ---
    @app.get("/api/history")
    def api_history(mmsi: str, minutes: int = 180):
        mm = [x.strip() for x in mmsi.split(",") if x.strip()]
        if not mm:
            return JSONResponse({})
        since = int(__import__("time").time()) - max(1, minutes) * 60
        out = db.query_history(mm, since)
        return JSONResponse(out)

    # --- WebSocket: tilaus valittuihin MMSI:hin ---
    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await ws_mgr.register(ws)
        try:
            while True:
                raw = await ws.receive_text()
                await ws_mgr.handle_message(ws, raw)
        except WebSocketDisconnect:
            pass
        finally:
            ws_mgr.unregister(ws)

    return app