# app/db.py
import sqlite3
import time
from typing import Dict, Iterable, List, Optional, Tuple
from threading import RLock
import threading
from .config import settings
from . import state
 
_db_lock = RLock()
_local = threading.local()

def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def get_db() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = connect()
    return _local.conn

def init_schema() -> None:
    db = get_db()
    with _db_lock, db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS vessel_latest (
            mmsi TEXT PRIMARY KEY,
            name TEXT,
            call_sign TEXT,
            type INTEGER,
            destination TEXT,
            last_lat REAL,
            last_lon REAL,
            last_time INTEGER,
            sog REAL,
            cog REAL,
            heading REAL,
            meta_ts_ms INTEGER,
            updated_ms INTEGER
        );
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS vessel_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mmsi TEXT NOT NULL,
            ts INTEGER NOT NULL,        -- 15 min kohdistettu aikaleima (sekunteina)
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            sog REAL,
            cog REAL,
            heading REAL
        );
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_samples_mmsi_ts ON vessel_samples(mmsi, ts);")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_samples_mmsi_ts ON vessel_samples(mmsi, ts);")

def upsert_latest(mmsi: str, loc: Optional[dict] = None, meta: Optional[dict] = None) -> None:
    """Päivitä viimeisin rivi yhdellä UPSERTillä."""
    name = meta.get("name") if meta else None
    call_sign = meta.get("callSign") if meta else None
    vtype = meta.get("type") if meta else None
    dest = meta.get("destination") if meta else None
    meta_ts_ms = meta.get("timestamp") if meta else None

    last_lat = loc.get("lat") if loc else None
    last_lon = loc.get("lon") if loc else None
    last_time = loc.get("time") if loc else None
    sog = loc.get("sog") if loc else None
    cog = loc.get("cog") if loc else None
    heading = loc.get("heading") if loc else None

    updated_ms = int(time.time() * 1000)

    db = get_db()
    with _db_lock, db:
        db.execute("""
        INSERT INTO vessel_latest
            (mmsi, name, call_sign, type, destination, last_lat, last_lon, last_time, sog, cog, heading, meta_ts_ms, updated_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(mmsi) DO UPDATE SET
            name = COALESCE(excluded.name, vessel_latest.name),
            call_sign = COALESCE(excluded.call_sign, vessel_latest.call_sign),
            type = COALESCE(excluded.type, vessel_latest.type),
            destination = COALESCE(excluded.destination, vessel_latest.destination),
            last_lat = COALESCE(excluded.last_lat, vessel_latest.last_lat),
            last_lon = COALESCE(excluded.last_lon, vessel_latest.last_lon),
            last_time = COALESCE(excluded.last_time, vessel_latest.last_time),
            sog = COALESCE(excluded.sog, vessel_latest.sog),
            cog = COALESCE(excluded.cog, vessel_latest.cog),
            heading = COALESCE(excluded.heading, vessel_latest.heading),
            meta_ts_ms = COALESCE(excluded.meta_ts_ms, vessel_latest.meta_ts_ms),
            updated_ms = excluded.updated_ms
        """, (mmsi, name, call_sign, vtype, dest, last_lat, last_lon, last_time, sog, cog, heading, meta_ts_ms, updated_ms))

def insert_snapshot_rows(rows: List[Tuple[str, int, float, float, Optional[float], Optional[float], Optional[float]]]) -> None:
    if not rows:
        return
    db = get_db()
    with _db_lock, db:
        db.executemany("""
            INSERT OR IGNORE INTO vessel_samples (mmsi, ts, lat, lon, sog, cog, heading)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, rows)

def insert_snapshot_for_mmsis(mmsis: Iterable[str], ts_floor: int) -> None:
    """Kerää state.latestistä rivit vain annetuista MMSI:stä ja kirjoita 15 min näyte."""
    out: List[Tuple[str, int, float, float, Optional[float], Optional[float], Optional[float]]] = []
    with state.latest_lock:
        for mmsi in mmsis:
            v = state.latest.get(mmsi)
            if not v or not v.get("loc"):  # ei vielä sijaintia
                continue
            loc = v["loc"]
            out.append((
                mmsi, ts_floor,
                loc.get("lat"), loc.get("lon"),
                loc.get("sog"), loc.get("cog"), loc.get("heading")
            ))
    insert_snapshot_rows(out)

def prune_history(older_than_minutes: int = 24 * 60) -> None:
    cutoff = int(time.time()) - older_than_minutes * 60
    db = get_db()
    with _db_lock, db:
        db.execute("DELETE FROM vessel_samples WHERE ts < ?", (cutoff,))

def insert_snapshot_for_all(ts_floor: int) -> None:
    """Kerää state.latestistä rivit kaikista MMSI:stä ja kirjoita 15 min näyte."""
    out: List[Tuple[str, int, float, float, Optional[float], Optional[float], Optional[float]]] = []
    with state.latest_lock:
        for mmsi, v in state.latest.items():
            if not v or not v.get("loc"):  # ei vielä sijaintia
                continue
            loc = v["loc"]
            out.append((
                mmsi, ts_floor,
                loc.get("lat"), loc.get("lon"),
                loc.get("sog"), loc.get("cog"), loc.get("heading")
            ))
    insert_snapshot_rows(out)

def query_vessels(q: Optional[str] = None, limit: int = 2000) -> List[Tuple[str, str]]:
    sql = "SELECT mmsi, COALESCE(name,'') FROM vessel_latest"
    params: Tuple = ()
    if q:
        sql += " WHERE mmsi LIKE ? OR name LIKE ?"
        like = f"%{q}%"
        params = (like, like)
    sql += " ORDER BY name COLLATE NOCASE ASC LIMIT ?"
    params = params + (limit,)
    db = get_db()
    # Read without lock to allow concurrency during heavy MQTT writes
    rows = db.execute(sql, params).fetchall()
    return rows

def query_history(mmsis: List[str], since_sec: int) -> Dict[str, List[dict]]:
    if not mmsis:
        return {}
    placeholders = ",".join("?" * len(mmsis))
    sql = f"""
        SELECT mmsi, ts, lat, lon, sog, cog, heading
        FROM vessel_samples
        WHERE mmsi IN ({placeholders}) AND ts >= ?
        ORDER BY mmsi, ts ASC
    """
    params = (*mmsis, since_sec)
    db = get_db()
    # Read without lock to allow concurrency during heavy MQTT writes
    rows = db.execute(sql, params).fetchall()
    out = {m: [] for m in mmsis}
    for m, ts, lat, lon, sog, cog, hdg in rows:
        out[m].append({"ts": ts, "lat": lat, "lon": lon, "sog": sog, "cog": cog, "heading": hdg})
    return out

# Alusta skeema moduulin latauksen yhteydessä
init_schema()