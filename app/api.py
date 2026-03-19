# app/api.py
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path

from contextlib import asynccontextmanager
import asyncio

from .config import settings
from . import db, state
from .ws_manager import WebSocketManager
from .mqtt_client import MqttService
from .snapshot import sampler_task

TEMPLATES = Path(__file__).parent / "templates"

def create_app(ws_mgr: WebSocketManager) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        loop = asyncio.get_running_loop()
        
        # Start MQTT client
        mqtt = MqttService(ws_mgr, loop)
        mqtt.start()

        # Start sampler task
        s_task = asyncio.create_task(sampler_task(ws_mgr))
        
        yield
        
        s_task.cancel()

    app = FastAPI(lifespan=lifespan)

    # --- UI ---
    @app.get("/")
    def root():
        return HTMLResponse(
            (TEMPLATES / "map_ui.html").read_text(encoding="utf-8")
        )

    @app.get("/simple")
    def simple_ui():
        return HTMLResponse(
            (TEMPLATES / "simple_ui.html").read_text(encoding="utf-8")
        )

    # --- API: vessel catalog (name/MMSI search) ---
    @app.get("/api/vessels")
    def api_vessels(q: Optional[str] = Query(default=None, description="Filter by name or MMSI")):
        rows = db.query_vessels(q=q, limit=2000)
        return JSONResponse([{"mmsi": r[0], "name": r[1]} for r in rows])

    # --- API: all vessels with current position (for initial map load) ---
    @app.get("/api/vessels/live")
    def api_vessels_live():
        result = []
        with state.latest_lock:
            vessels_copy = list(state.latest.items())
            
        for mmsi, v in vessels_copy:
            loc = v.get("loc")
            if not loc or loc.get("lat") is None or loc.get("lon") is None:
                continue
            meta = v.get("meta", {})
            result.append({
                "mmsi": mmsi,
                "name": meta.get("name", ""),
                "type": meta.get("type"),
                "destination": meta.get("destination", ""),
                "lat": loc["lat"],
                "lon": loc["lon"],
                "sog": loc.get("sog"),
                "cog": loc.get("cog"),
                "heading": loc.get("heading"),
                "lastSeen": v.get("last_seen"),
            })
        return JSONResponse(result)

    # --- API: history (15-min samples) ---
    @app.get("/api/history")
    def api_history(mmsi: str, minutes: int = 180):
        mm = [x.strip() for x in mmsi.split(",") if x.strip()]
        if not mm:
            return JSONResponse({})
        since = int(__import__("time").time()) - max(1, minutes) * 60
        out = db.query_history(mm, since)
        return JSONResponse(out)

    # --- WebSocket: live vessel updates ---
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