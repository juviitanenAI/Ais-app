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
            print(f"[SNAPSHOT] Wrote snapshot at {ts_floor}")
        except Exception as e:
            print(f"[SNAPSHOT] Error in sampler_task: {e}")

async def snapshot_now_for_mmsis(mmsis: Iterable[str]):
    """Ota välitön näyte juuri valituille aluksille (kohti lähintä 15 min rajaa)."""
    ts_floor = floor_to_interval(int(time.time()), settings.SNAPSHOT_INTERVAL_SEC)
    db.insert_snapshot_for_mmsis(set(mmsis), ts_floor)