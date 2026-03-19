# app/db.py
import sqlite3
import time
from typing import Dict, Iterable, List, Optional, Tuple
from threading import RLock
from .config import settings
from . import state
 
_db_lock = RLock()

def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

db = connect()

def init_schema() -> None:
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
    with _db_lock, db:
        row = db.execute("""
            SELECT name, call_sign, type, destination, last_lat, last_lon, last_time, sog, cog, heading, meta_ts_ms
            FROM vessel_latest WHERE mmsi=?
        """, (mmsi,)).fetchone()

        name, call_sign, vtype, dest, last_lat, last_lon, last_time, sog, cog, heading, meta_ts_ms = (row or (None,)*11)

        if meta:
            name = meta.get("name", name)
            call_sign = meta.get("callSign", call_sign)
            vtype = meta.get("type", vtype)
            dest = meta.get("destination", dest)
            meta_ts_ms = meta.get("timestamp", meta_ts_ms)

        if loc:
            last_lat = loc.get("lat", last_lat)
            last_lon = loc.get("lon", last_lon)
            last_time = loc.get("time", last_time)  # sekunteina
            sog = loc.get("sog", sog)
            cog = loc.get("cog", cog)
            heading = loc.get("heading", heading)

        updated_ms = int(time.time() * 1000)

        db.execute("""
        INSERT INTO vessel_latest
            (mmsi, name, call_sign, type, destination, last_lat, last_lon, last_time, sog, cog, heading, meta_ts_ms, updated_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(mmsi) DO UPDATE SET
            name=excluded.name,
            call_sign=excluded.call_sign,
            type=excluded.type,
            destination=excluded.destination,
            last_lat=excluded.last_lat,
            last_lon=excluded.last_lon,
            last_time=excluded.last_time,
            sog=excluded.sog,
            cog=excluded.cog,
            heading=excluded.heading,
            meta_ts_ms=excluded.meta_ts_ms,
            updated_ms=excluded.updated_ms
        """, (mmsi, name, call_sign, vtype, dest, last_lat, last_lon, last_time, sog, cog, heading, meta_ts_ms, updated_ms))

def insert_snapshot_rows(rows: List[Tuple[str, int, float, float, Optional[float], Optional[float], Optional[float]]]) -> None:
    if not rows:
        return
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
    with _db_lock:
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
    with _db_lock:
        rows = db.execute(sql, params).fetchall()
    out = {m: [] for m in mmsis}
    for m, ts, lat, lon, sog, cog, hdg in rows:
        out[m].append({"ts": ts, "lat": lat, "lon": lon, "sog": sog, "cog": cog, "heading": hdg})
    return out

# Alusta skeema moduulin latauksen yhteydessä
init_schema()