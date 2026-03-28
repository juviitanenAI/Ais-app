# app/state.py
from typing import Dict
from threading import RLock

# Uusin live-tila muistiin (per MMSI)
latest_lock = RLock()
latest: Dict[str, dict] = {}  # mmsi -> {"loc": {...}, "meta": {...}, "last_seen": epochSec}

# Alusten tyyppien tyylit (vessel_types-taulusta)
vessel_type_cache: Dict[str, dict] = {} # code -> {color, desc_fi, desc_en, category}

# Valmiustila (asetetaan True kun lifespan-alustus on valmis)
is_ready: bool = False

# Poijujen / mittausasemien tila (site_number -> data)
buoys_lock = RLock()
buoys: Dict[int, dict] = {}