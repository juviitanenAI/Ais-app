# app/api.py
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path

from contextlib import asynccontextmanager
import asyncio

from datetime import datetime, timezone, timedelta
from .config import settings
from . import db, state
from .ws_manager import WebSocketManager
from .mqtt_client import MqttService
from .buoy_service import BuoyService
from .snapshot import sampler_task, flusher_task
from .scripts.update_vessel_types import update_vessel_types

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

def create_app(ws_mgr: WebSocketManager) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        loop = asyncio.get_running_loop()

        # Resolve skip-integrity BEFORE opening the DB — connect() itself
        # can trigger WAL recovery which is the actual expensive operation.
        skip_file = Path(".skip_integrity")
        should_check = settings.CHECK_INTEGRITY
        if skip_file.exists():
            should_check = False
            try:
                skip_file.unlink()
                print("[Lifespan] Integrity skip file found and deleted. Skipping check.", flush=True)
            except Exception as e:
                print(f"[Lifespan] Failed to remove integrity skip file: {e}", flush=True)

        # Schema init (first DB connection — may trigger WAL recovery after dirty kills)
        import time as _time
        t0 = _time.monotonic()
        print("[Lifespan] Initializing DB schemas...", flush=True)
        await loop.run_in_executor(None, db.init_schema)
        await loop.run_in_executor(None, db.init_cache_schema)
        elapsed = _time.monotonic() - t0
        print(f"[Lifespan] DB schemas ready ({elapsed:.1f}s)", flush=True)

        # Integrity check (if enabled and not skipped)
        if should_check:
            await loop.run_in_executor(None, db.check_integrity)

        # Load initial state from DB
        try:
            print("[Lifespan] Loading initial vessel state from DB...", flush=True)
            await loop.run_in_executor(None, db.load_latest_into_state)
            print(f"[Lifespan] Initial state loaded. state.latest has {len(state.latest)} vessels.", flush=True)
            
            print("[Lifespan] Loading initial buoy state from DB...", flush=True)
            buoy_rows = await loop.run_in_executor(None, db.query_buoys)
            
            buoy_cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.BUOY_RETENTION_MINUTES)
            loaded_count = 0
            
            with state.buoys_lock:
                for b in buoy_rows:
                    last_upd = b.get("lastUpdate")
                    is_stale = False
                    if last_upd:
                        try:
                            dt = datetime.fromisoformat(last_upd.replace("Z", "+00:00"))
                            if dt < buoy_cutoff:
                                is_stale = True
                        except ValueError:
                            pass
                    
                    if not is_stale:
                        state.buoys[b["siteNumber"]] = {
                            "lat": b["lat"],
                            "lon": b["lon"],
                            "data": b["properties"],
                            "dataUpdatedTime": b["dataUpdatedTime"]
                        }
                        loaded_count += 1
            print(f"[Lifespan] Initial buoy state loaded. state.buoys has {loaded_count} stations (skipped {len(buoy_rows) - loaded_count} stale).", flush=True)
        except Exception as e:
            print(f"[Lifespan] Initial state load failed: {e}", flush=True)

        # Update vessel types from Digitraffic (run in background)
        def update_and_cache():
            import time
            start_time = time.time()
            try:
                print("[Lifespan] Starting background vessel type update...", flush=True)
                update_vessel_types()
                new_types = db.query_vessel_types()
                state.vessel_type_cache.update(new_types)
                print(f"[Lifespan] Vessel types updated successfully. Cache now has {len(state.vessel_type_cache)} entries. Took {time.time() - start_time:.2f}s", flush=True)
            except Exception as e:
                print(f"[Lifespan] Vessel type update failed after {time.time() - start_time:.2f}s: {e}", flush=True)

        # 1. Update once on startup
        loop.run_in_executor(None, update_and_cache)
        
        # Schedule weekly vessel type update
        async def weekly_updater():
            while True:
                await asyncio.sleep(7 * 24 * 3600)
                loop.run_in_executor(None, update_and_cache)
        
        up_task = asyncio.create_task(weekly_updater())

        # Initial cache load
        try:
            state.vessel_type_cache.update(db.query_vessel_types())
        except Exception as e:
            print(f"[Lifespan] Initial cache load failed: {e}", flush=True)

        # Start MQTT client
        mqtt = MqttService(ws_mgr, loop)
        mqtt.start()

        # Start sampler task
        s_task = asyncio.create_task(sampler_task(ws_mgr))
        
        # Start flusher task
        f_task = asyncio.create_task(flusher_task())
        
        # Start Buoy service
        buoy_service = BuoyService(ws_mgr, loop)
        buoy_service.start()
        
        # 4. Background Cache Checks (Heatmap & Trends)
        def check_caches_and_rebuild():
            try:
                # Give the system 60 seconds to settle before heavy background rebuild
                _time.sleep(60)
                
                # Check Heatmap
                heatmap_data = db.query_heatmap_cache(1440)
                if not heatmap_data:
                    sample_count = db.count_samples()
                    if sample_count > 0:
                        print(f"[Heatmap] Cache empty but {sample_count} samples found. Triggering initial rebuild...")
                        db.rebuild_heatmap_cache()
                        print("[Heatmap] Initial automatic rebuild complete.")
                
                # Check Trends
                trends_data = db.query_trends_cache(1440)
                if not trends_data:
                    sample_count = db.count_samples()
                    if sample_count > 0:
                        print(f"[Trends] Cache empty but {sample_count} samples found. Triggering initial rebuild...")
                        db.rebuild_trends_cache()
                        print("[Trends] Initial automatic rebuild complete.")
                        
            except db.AlreadyRebuildingError:
                # This might happen if a user manually triggered a rebuild during the 60s sleep
                print("[Lifespan] Startup rebuild skipped: already in progress.")
            except Exception as e:
                print(f"[Lifespan] Automatic startup check/rebuild failed: {e}")

        loop.run_in_executor(None, check_caches_and_rebuild)

        state.is_ready = True
        yield
        
        s_task.cancel()
        f_task.cancel()
        up_task.cancel()
        
        # Ensure DB is cleanly closed on lifespan end (shutdown)
        db.shutdown()

    app = FastAPI(lifespan=lifespan)

    @app.api_route("/api/up", methods=["GET", "HEAD"])
    async def up():
        """Health check endpoint. Returns 200 if ready, 503 if still initializing."""
        if not state.is_ready:
            return Response(status_code=503)
        return Response(status_code=200)
    

    # --- UI ---
    @app.get("/")
    def root():
        idx_path = FRONTEND_DIST / "index.html"
        if idx_path.exists():
            return HTMLResponse(idx_path.read_text(encoding="utf-8"))
        return HTMLResponse("Svelte frontend not built. Run 'npm run build' in frontend directory.", status_code=404)

    # --- API: vessel catalog (name/MMSI search) ---
    @app.get("/api/vessels")
    def api_vessels(
        q: Optional[str] = Query(default=None, description="Filter by name or MMSI"),
        category: Optional[List[str]] = Query(default=None, description="Filter by vessel categories")
    ):
        rows = db.query_vessels(q=q, categories=category, limit=2000)
        return JSONResponse([
            {"mmsi": r[0], "name": r[1], "is_live": bool(r[2]), "latest_ts": r[3]} 
            for r in rows
        ])

    # --- API: vessel categories (for dropdown/legend) ---
    @app.get("/api/vessel-categories")
    def api_vessel_categories():
        return JSONResponse(db.query_vessel_categories())

    # --- API: buoy measurements ---
    @app.get("/api/buoys")
    def api_buoys():
        with state.buoys_lock:
            # Convert siteNumber keys to strings if needed or just return list
            return JSONResponse(list(state.buoys.values()))

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
                    "category": style.get("category", "Other")
                },
                "destination": meta.get("destination", ""),
                "lat": loc["lat"],
                "lon": loc["lon"],
                "sog": loc.get("sog"),
                "cog": loc.get("cog"),
                "heading": loc.get("heading"),
                "lastSeen": v.get("last_seen"),
                "imo": meta.get("imo")
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

    # --- API: route heatmap cache ---
    @app.get("/api/heatmap")
    def api_heatmap(minutes: int = 1440, category: Optional[str] = None):
        # Allow windows: 12h (720), 24h (1440), 3d (4320), 1w (10080)
        if minutes not in [720, 1440, 4320, 10080]:
            minutes = 1440
        data = db.query_heatmap_cache(minutes, category)
        return JSONResponse(data)

    @app.post("/api/heatmap/rebuild")
    async def api_rebuild_heatmap():
        """Trigger a manual rebuild of the heatmap cache."""
        loop = asyncio.get_running_loop()
        try:
            # Run in executor to avoid blocking the event loop
            await loop.run_in_executor(None, db.rebuild_heatmap_cache)
            return JSONResponse({"status": "success", "message": "Heatmap cache rebuild complete"})
        except db.AlreadyRebuildingError as e:
            return JSONResponse({"status": "ignored", "message": str(e)}, status_code=409)
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

    @app.post("/api/stats/activity/rebuild")
    async def api_rebuild_trends():
        """Trigger a manual rebuild of the activity trends cache."""
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, db.rebuild_trends_cache)
            return JSONResponse({"status": "success", "message": "Trends cache rebuild complete"})
        except db.AlreadyRebuildingError as e:
            return JSONResponse({"status": "ignored", "message": str(e)}, status_code=409)
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

    # --- API: stats activity (reads from pre-computed cache) ---
    @app.get("/api/stats/activity")
    def api_stats_activity(minutes: int = 1440):
        if minutes <= 0:
            minutes = 1440
        # Try cache first (instant)
        cached = db.query_trends_cache(minutes)
        if cached is not None:
            return JSONResponse(cached)
        # Fallback to live computation if cache miss
        data = db.query_stats_activity(minutes)
        return JSONResponse(data)

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

    @app.post("/api/admin/shutdown")
    async def admin_shutdown():
        """Administrative shutdown endpoint. Requires some form of auth/protection in production."""
        # For now, we trust internal network or basic env-check
        import os
        import signal
        print("[Admin] Shutdown requested via API.")
        # Trigger graceful exit of the parent process (uvicorn)
        os.kill(os.getpid(), signal.SIGINT)
        return JSONResponse({"status": "shutdown_initiated"})

    return app