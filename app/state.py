# app/state.py
from typing import Dict
from threading import RLock

# Uusin live-tila muistiin (per MMSI)
latest_lock = RLock()
latest: Dict[str, dict] = {}  # mmsi -> {"loc": {...}, "meta": {...}, "last_seen": epochSec}