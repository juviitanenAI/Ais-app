# main.py
import asyncio
from pathlib import Path

import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api import create_app
from app.ws_manager import WebSocketManager as WSManager
from app.mqtt_client import MqttService
from app.snapshot import sampler_task


def build_app_and_services():
    """
    Build WS manager, FastAPI app, mount static, wire favicon,
    start MQTT service, and schedule the 15-min sampler.
    """
    # Create the asyncio loop (so we can pass it to MQTT for safe cross-thread callbacks)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # WS manager shared across HTTP + MQTT
    ws_mgr = WSManager()

    # Create FastAPI app (routes: /, /api/vessels, /api/history, /ws)
    app = create_app(ws_mgr)

    # ---- Static & favicon (safe only AFTER app exists) ----
    # static folder: app/static
    static_dir = Path(__file__).parent / "app" / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    favicon_path = static_dir / "favicon.ico"

    @app.get("/favicon.ico")
    async def favicon():
        # If you don't have a favicon yet, you can add one to app/static/favicon.ico later.
        if favicon_path.exists():
            return FileResponse(str(favicon_path), media_type="image/x-icon")
        # Return 204 No Content if missing (avoids 404 spam in logs)
        from fastapi import Response
        return Response(status_code=204)

    # ---- Start MQTT in a background thread ----
    mqtt = MqttService(ws_mgr, loop)
    mqtt.start()  # non-blocking: launches a daemon thread

    # ---- Schedule the 15-minute sampler (records only tracked vessels) ----
    loop.create_task(sampler_task(ws_mgr))

    return app, loop


if __name__ == "__main__":
    app, loop = build_app_and_services()

    # Run Uvicorn (HTTP server) on the same asyncio loop
    # If port 8000 is busy, change port=8080 (or any free port)
    uvicorn.run(app, host="0.0.0.0", port=8000, loop="asyncio")