import asyncio
import httpx
import time
from .config import settings
from . import db, state
from .ws_manager import WebSocketManager

class BuoyService:
    """
    Service to periodically fetch buoy measurements from Digitraffic.
    Updates every 30 minutes as per data update frequency.
    """
    def __init__(self, ws_mgr: WebSocketManager, loop: asyncio.AbstractEventLoop):
        self.ws_mgr = ws_mgr
        self.loop = loop
        self.running = False

    async def fetch_and_process(self):
        try:
            print("[BuoyService] Fetching latest measurements...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    settings.BUOY_SSE_URL,
                    headers={"Digitraffic-User": settings.DIGITRAFFIC_USER}
                )
                if response.status_code != 200:
                    print(f"[BuoyService] Fetch failed with status {response.status_code}")
                    return

                data = response.json()
                data_updated_time = data.get("dataUpdatedTime")
                if not data_updated_time:
                    print("[BuoyService] Response missing dataUpdatedTime")
                    return

                # Check if we already have this update
                latest_known = db.get_latest_buoy_update_time()
                if latest_known == data_updated_time:
                    print(f"[BuoyService] Data is already up to date ({data_updated_time})")
                    return

                print(f"[BuoyService] New data found: {data_updated_time}. Updating...")
                features = data.get("features", [])
                
                # Update DB
                await self.loop.run_in_executor(None, db.upsert_buoys, features, data_updated_time)
                
                # Update State
                with state.buoys_lock:
                    for f in features:
                        props = f["properties"]
                        site_number = props["siteNumber"]
                        state.buoys[site_number] = {
                            "lat": f["geometry"]["coordinates"][1],
                            "lon": f["geometry"]["coordinates"][0],
                            "data": props,
                            "dataUpdatedTime": data_updated_time
                        }

                # Broadcast to WS clients
                message = {
                    "type": "buoys",
                    "dataUpdatedTime": data_updated_time,
                    "count": len(features)
                }
                await self.ws_mgr.broadcast_buoy(message)
                print(f"[BuoyService] Successfully processed {len(features)} buoys.")

        except Exception as e:
            print(f"[BuoyService] Error in fetch_and_process: {e}")

    async def run(self):
        self.running = True
        # Initial fetch on startup
        await self.fetch_and_process()
        
        while self.running:
            # Poll every 15 minutes to caught the 30-minute updates reliably
            await asyncio.sleep(15 * 60)
            await self.fetch_and_process()

    def start(self):
        asyncio.run_coroutine_threadsafe(self.run(), self.loop)

    def stop(self):
        self.running = False
