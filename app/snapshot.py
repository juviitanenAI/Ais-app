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
    """Aja ikuisesti: ota 15 min välein näytteet VAIN seurannassa oleville MMSI:lle."""
    while True:
        now = int(time.time())
        next_tick = floor_to_interval(now, settings.SNAPSHOT_INTERVAL_SEC) + settings.SNAPSHOT_INTERVAL_SEC
        await asyncio.sleep(max(0, next_tick - now))
        ts_floor = floor_to_interval(int(time.time()), settings.SNAPSHOT_INTERVAL_SEC)
        tracked = ws_mgr.tracked_union()
        db.insert_snapshot_for_mmsis(tracked, ts_floor)
        db.prune_history(older_than_minutes=24*60)

async def snapshot_now_for_mmsis(mmsis: Iterable[str]):
    """Ota välitön näyte juuri valituille aluksille (kohti lähintä 15 min rajaa)."""
    ts_floor = floor_to_interval(int(time.time()), settings.SNAPSHOT_INTERVAL_SEC)
    db.insert_snapshot_for_mmsis(set(mmsis), ts_floor)