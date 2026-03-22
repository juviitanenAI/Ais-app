# app/snapshot.py
import asyncio
import time
from typing import Iterable, Set
from .config import settings
from . import db
from .ws_manager import WebSocketManager

def floor_to_interval(ts: int, interval: int) -> int:
    return ts - (ts % interval)

async def sampler_task(ws_mgr: WebSocketManager):
    """Aja ikuisesti: ota 15 sek välein näytteet KAIKILLE alueen MMSI:lle."""
    print("[SNAPSHOT] Sampler task started.")
    while True:
        try:
            now = int(time.time())
            next_tick = floor_to_interval(now, settings.SNAPSHOT_INTERVAL_SEC) + settings.SNAPSHOT_INTERVAL_SEC
            sleep_time = max(0, next_tick - now)
            await asyncio.sleep(sleep_time)
            
            ts_floor = floor_to_interval(int(time.time()), settings.SNAPSHOT_INTERVAL_SEC)
            db.insert_snapshot_for_all(ts_floor)
            db.prune_history(older_than_minutes=settings.SNAPSHOT_RETENTION_MINUTES)
            db.prune_vessel_latest(older_than_minutes=settings.SNAPSHOT_RETENTION_MINUTES)

            # Prune in-memory state.latest
            with state.latest_lock:
                cutoff_ts = int(time.time()) - settings.SNAPSHOT_RETENTION_MINUTES * 60
                stale_mmsis = [mmsi for mmsi, v in state.latest.items() if v.get("last_seen", 0) < cutoff_ts]
                for mmsi in stale_mmsis:
                    del state.latest[mmsi]

            print(f"[SNAPSHOT] Wrote snapshot and pruned state/db at {ts_floor}")

            # Trigger trends cache rebuild every 15 minutes
            if ts_floor % (15 * 60) == 0:
                print(f"[SNAPSHOT] Triggering timed trends rebuild at {ts_floor}...")
                asyncio.create_task(asyncio.to_thread(db.rebuild_trends_cache))

            # Trigger heatmap rebuild every 60 minutes (on the hour)
            if ts_floor % (60 * 60) == 0:
                print(f"[SNAPSHOT] Triggering timed heatmap rebuild at {ts_floor}...")
                asyncio.create_task(asyncio.to_thread(db.rebuild_heatmap_cache))
        except Exception as e:
            print(f"[SNAPSHOT] Error in sampler_task: {e}")

async def snapshot_now_for_mmsis(mmsis: Iterable[str]):
    """Ota välitön näyte juuri valituille aluksille (kohti lähintä 15 min rajaa)."""
    ts_floor = floor_to_interval(int(time.time()), settings.SNAPSHOT_INTERVAL_SEC)
    db.insert_snapshot_for_mmsis(set(mmsis), ts_floor)