# main.py
import asyncio
import sys
from pathlib import Path

import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api import create_app
from app.ws_manager import WebSocketManager as WSManager
from app import db

def build_app_and_services():
    """
    Build WS manager, FastAPI app, mount static, wire favicon,
    start MQTT service, and schedule the 15-min sampler.
    """
    # WS manager shared across HTTP + MQTT
    ws_mgr = WSManager()

    if "--calculate-views" in sys.argv:
        print("[Startup] --calculate-views flag detected. Building heatmap & trends cache...")
        try:
            db.init_schema() # ensure schema is ready before building cache
            db.rebuild_heatmap_cache()
            print("[Startup] Heatmap cache built.")
            db.rebuild_trends_cache()
            print("[Startup] Trends cache built.")
        except Exception as e:
            print(f"[Startup] Failed to build cache: {e}")

    # Create FastAPI app (routes: /, /api/vessels, /api/history, /ws)
    app = create_app(ws_mgr)

    # Vite compiled frontend assets
    frontend_dist = Path(__file__).parent / "frontend" / "dist"
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/favicon.ico")
    async def favicon():
        fav = frontend_dist / "favicon.ico"
        if fav.exists():
            return FileResponse(str(fav), media_type="image/x-icon")
        from fastapi import Response
        return Response(status_code=204)

    return app


import atexit
atexit.register(db.shutdown)
app = build_app_and_services()

if __name__ == "__main__":
    import uvicorn
    # Run Uvicorn (HTTP server) on the same asyncio loop
    # If port 8000 is busy, change port=8080 (or any free port)
    uvicorn.run(app, host="0.0.0.0", port=8000)