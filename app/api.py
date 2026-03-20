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
from .scripts.update_vessel_types import update_vessel_types

TEMPLATES = Path(__file__).parent / "templates"

def create_app(ws_mgr: WebSocketManager) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Explicit initialization
        db.init_schema()

        loop = asyncio.get_running_loop()

        # Update vessel types from Digitraffic (run in background)
        def update_and_cache():
            import time
            start_time = time.time()
            try:
                print("[Lifespan] Starting background vessel type update...")
                update_vessel_types()
                new_types = db.query_vessel_types()
                state.vessel_type_cache.update(new_types)
                print(f"[Lifespan] Vessel types updated successfully. Cache now has {len(state.vessel_type_cache)} entries. Took {time.time() - start_time:.2f}s")
            except Exception as e:
                print(f"[Lifespan] Vessel type update failed after {time.time() - start_time:.2f}s: {e}")

        # 1. Update once on startup
        loop.run_in_executor(None, update_and_cache)
        
        # 2. Schedule weekly
        async def weekly_updater():
            while True:
                await asyncio.sleep(7 * 24 * 3600)  # Wait 1 week
                loop.run_in_executor(None, update_and_cache)
        
        up_task = asyncio.create_task(weekly_updater())

        # Initial cache load
        try:
            state.vessel_type_cache.update(db.query_vessel_types())
        except Exception as e:
            print(f"[Lifespan] Initial cache load failed: {e}")

        # Start MQTT client
        mqtt = MqttService(ws_mgr, loop)
        mqtt.start()

        # Start sampler task
        s_task = asyncio.create_task(sampler_task(ws_mgr))
        
        yield
        
        s_task.cancel()
        up_task.cancel()

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
        return JSONResponse([
            {"mmsi": r[0], "name": r[1], "is_live": bool(r[2]), "latest_ts": r[3]} 
            for r in rows
        ])

    # --- API: vessel types (for legend and styling) ---
    @app.get("/api/vessel-types")
    def api_vessel_types():
        return JSONResponse(state.vessel_type_cache)

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
            vtype_code = str(meta.get("type", ""))
            style = state.vessel_type_cache.get(vtype_code, {})

            result.append({
                "mmsi": mmsi,
                "name": meta.get("name", ""),
                "type": meta.get("type"),
                "vtype_info": {
                    "color": style.get("color", "#8899aa"),
                    "label": style.get("desc_en") or style.get("desc_fi") or "Other",
                    "category": style.get("category", "other")
                },
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