# app/db.py
import json
import sqlite3
import time
from typing import Dict, Iterable, List, Optional, Tuple
from threading import RLock
import threading
from .config import settings
from . import state
 
_db_lock = RLock()
_rebuild_lock = RLock() # Lock to prevent multiple concurrent rebuilds
_local = threading.local()
_db_path = settings.DB_PATH

def set_db_path(path: str):
    global _db_path
    _db_path = path
    # Clear local connection if exists
    if hasattr(_local, "conn"):
        try:
            _local.conn.close()
        except:
            pass
        del _local.conn

def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    # Changed from NORMAL to FULL for better crash safety (fsync on WAL frames)
    conn.execute("PRAGMA synchronous=FULL;")
    # Ensure WAL doesn't grow indefinitely
    conn.execute("PRAGMA wal_autocheckpoint=1000;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

def get_db() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = connect()
    return _local.conn

def with_db_retry(func):
    """Decorator to retry DB operations if 'database is locked' occurs."""
    import functools
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        last_err = None
        for attempt in range(10):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower():
                    last_err = e
                    backoff = min(1.0 * (attempt + 1), 5.0)
                    time.sleep(backoff)
                    continue
                raise
        print(f"[DB] Retry failed after 10 attempts: {last_err}")
        return None
    return wrapper

@with_db_retry
def upsert_buoys(features: List[dict], data_updated_time: str) -> None:
    db = get_db()
    with _db_lock, db:
        for f in features:
            props = f["properties"]
            geom = f["geometry"]
            site_number = props["siteNumber"]
            name = props.get("siteName")
            stype = props.get("siteType")
            lon, lat = geom["coordinates"]
            last_update = props.get("lastUpdate")
            
            db.execute("""
                INSERT INTO buoy_latest (site_number, name, type, lat, lon, last_update, data_updated_time, properties)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(site_number) DO UPDATE SET
                    name = excluded.name,
                    type = excluded.type,
                    lat = excluded.lat,
                    lon = excluded.lon,
                    last_update = excluded.last_update,
                    data_updated_time = excluded.data_updated_time,
                    properties = excluded.properties
            """, (site_number, name, stype, lat, lon, last_update, data_updated_time, json.dumps(props)))
            
            # History: site_number + updated_time as PK
            db.execute("""
                INSERT OR IGNORE INTO buoy_history (site_number, lat, lon, last_update, data_updated_time, properties)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (site_number, lat, lon, last_update, data_updated_time, json.dumps(props)))

def query_buoys() -> List[dict]:
    db = get_db()
    rows = db.execute("SELECT site_number, name, type, lat, lon, last_update, data_updated_time, properties FROM buoy_latest").fetchall()
    return [{
        "siteNumber": r[0],
        "name": r[1],
        "type": r[2],
        "lat": r[3],
        "lon": r[4],
        "lastUpdate": r[5],
        "dataUpdatedTime": r[6],
        "properties": json.loads(r[7])
    } for r in rows]

def get_latest_buoy_update_time() -> Optional[str]:
    db = get_db()
    row = db.execute("SELECT MAX(data_updated_time) FROM buoy_latest").fetchone()
    return row[0] if row else None

def init_schema() -> None:
    db = get_db()
    with _db_lock, db:
        # Quick integrity verify on startup
        try:
            res = db.execute("PRAGMA integrity_check(100);").fetchone()
            if res and res[0] != "ok":
                print(f"[DB] WARNING: Integrity check failed: {res[0]}")
        except Exception as e:
            print(f"[DB] Integrity check error: {e}")

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
        db.execute("CREATE INDEX IF NOT EXISTS idx_samples_ts ON vessel_samples(ts);")

        # Alusten tyyppien kuvaukset ja värit
        db.execute("""
        CREATE TABLE IF NOT EXISTS vessel_types (
            code TEXT PRIMARY KEY,
            desc_fi TEXT,
            desc_en TEXT,
            color TEXT,
            category TEXT
        );
        """)

        db.execute("""
        CREATE TABLE IF NOT EXISTS heatmap_cache (
            time_window INTEGER,
            category TEXT,
            lat_grid REAL,
            lon_grid REAL,
            weight INTEGER,
            PRIMARY KEY (time_window, category, lat_grid, lon_grid)
        );
        """)

        db.execute("""
        CREATE TABLE IF NOT EXISTS activity_trends_cache (
            time_window INTEGER PRIMARY KEY,
            json_blob TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        );
        """)

        db.execute("""
        CREATE TABLE IF NOT EXISTS buoy_latest (
            site_number INTEGER PRIMARY KEY,
            name TEXT,
            type TEXT,
            lat REAL,
            lon REAL,
            last_update TEXT,
            data_updated_time TEXT,
            properties TEXT
        );
        """)

        db.execute("""
        CREATE TABLE IF NOT EXISTS buoy_history (
            site_number INTEGER,
            lat REAL,
            lon REAL,
            last_update TEXT,
            data_updated_time TEXT,
            properties TEXT,
            PRIMARY KEY (site_number, data_updated_time)
        );
        """)


@with_db_retry
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
        _upsert_latest_stmt(db, mmsi, name, call_sign, vtype, dest, last_lat, last_lon, last_time, sog, cog, heading, meta_ts_ms, updated_ms)

def _upsert_latest_stmt(db, mmsi, name, call_sign, vtype, dest, last_lat, last_lon, last_time, sog, cog, heading, meta_ts_ms, updated_ms):
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

@with_db_retry
def upsert_latest_batch(items: List[dict]) -> None:
    """Päivitä useita aluksia kerralla yhdessä transaktiossa."""
    if not items:
        return
    updated_ms = int(time.time() * 1000)
    db = get_db()
    with _db_lock, db:
        for item in items:
            mmsi = item["mmsi"]
            loc = item.get("loc") or {}
            meta = item.get("meta") or {}
            _upsert_latest_stmt(
                db, mmsi, 
                meta.get("name"), meta.get("callSign"), meta.get("type"), meta.get("destination"),
                loc.get("lat"), loc.get("lon"), loc.get("time"), loc.get("sog"), loc.get("cog"), loc.get("heading"),
                meta.get("timestamp"), updated_ms
            )

def load_latest_into_state() -> None:
    """Lataa viimeisimmät tunnetut sijainnit tietokannasta state.latest-sanakirjaan."""
    db = get_db()
    # Lataamme vain viimeisen 24h aikana nähdyt tai kaikki?
    # Käyttäjän toiveen mukaan "since we might be missing a bunch".
    # Otetaan kaikki vessel_latest -taulun rivit.
    rows = db.execute("""
        SELECT mmsi, name, call_sign, type, destination, last_lat, last_lon, last_time, sog, cog, heading, meta_ts_ms
        FROM vessel_latest
    """).fetchall()
    
    with state.latest_lock:
        for r in rows:
            mmsi = r[0]
            if mmsi in state.latest:
                continue
            
            # r[5] is last_lat, r[6] is last_lon
            loc = None
            if r[5] is not None and r[6] is not None:
                loc = {
                    "lat": r[5], "lon": r[6], "time": r[7],
                    "sog": r[8], "cog": r[9], "heading": r[10]
                }
            
            state.latest[mmsi] = {
                "loc": loc,
                "meta": {
                    "name": r[1], "callSign": r[2], "type": r[3],
                    "destination": r[4], "timestamp": r[11]
                },
                "last_seen": r[7] or (r[11] // 1000 if r[11] else int(time.time()))
            }

@with_db_retry
def upsert_vessel_type(code: str, desc_fi: str, desc_en: str, color: str, category: str) -> None:
    db = get_db()
    with _db_lock, db:
        db.execute("""
        INSERT INTO vessel_types (code, desc_fi, desc_en, color, category)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
            desc_fi = excluded.desc_fi,
            desc_en = excluded.desc_en,
            color = excluded.color,
            category = excluded.category
        """, (code, desc_fi, desc_en, color, category))

def query_vessel_types() -> Dict[str, dict]:
    db = get_db()
    rows = db.execute("SELECT code, desc_fi, desc_en, color, category FROM vessel_types").fetchall()
    return {r[0]: {"desc_fi": r[1], "desc_en": r[2], "color": r[3], "category": r[4]} for r in rows}

def query_vessel_categories() -> List[Dict[str, str]]:
    """Palauttaa uniikit kategoriat ja niille asetetun värin."""
    db = get_db()
    # Otetaan ensimmäinen löytyvä väri kategoriasta (pitäisi olla sama kaikilla saman kategorian aluksilla)
    rows = db.execute("""
        SELECT category, color 
        FROM vessel_types 
        GROUP BY category 
        ORDER BY category
    """).fetchall()
    return [{"name": r[0], "color": r[1]} for r in rows if r[0]]

@with_db_retry
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

@with_db_retry
def prune_history(older_than_minutes: int = 24 * 60) -> None:
    cutoff = int(time.time()) - older_than_minutes * 60
    db = get_db()
    with _db_lock, db:
        db.execute("DELETE FROM vessel_samples WHERE ts < ?", (cutoff,))
        # Prune trends cache rows whose window is entirely outside retention
        # (windows referencing data older than cutoff are stale)
        db.execute("DELETE FROM activity_trends_cache WHERE updated_at < ?", (cutoff,))

@with_db_retry
def prune_vessel_latest(older_than_minutes: int = 24 * 60) -> None:
    """Poista stale-alukset vessel_latest -taulusta (updated_ms perusteella)."""
    cutoff_ms = int((time.time() - older_than_minutes * 60) * 1000)
    db = get_db()
    with _db_lock, db:
        db.execute("DELETE FROM vessel_latest WHERE updated_ms < ?", (cutoff_ms,))

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

def query_vessels(q: Optional[str] = None, categories: Optional[List[str]] = None, limit: int = 2000) -> List[Tuple[str, str, int, int]]:
    params: List = []
    
    # Base filter for category if provided
    cat_filter_latest = ""
    cat_filter_samples = ""
    if categories:
        placeholders = ",".join("?" for _ in categories)
        cat_filter_latest = f"AND type IN (SELECT code FROM vessel_types WHERE LOWER(category) IN ({placeholders}))"
        cat_filter_samples = f"AND mmsi IN (SELECT mmsi FROM vessel_latest WHERE type IN (SELECT code FROM vessel_types WHERE LOWER(category) IN ({placeholders})))"
        params.extend([c.lower() for c in categories])

    if q:
        like = f"%{q}%"
        sql = f"""
            WITH LatestMatch AS (
                SELECT
                    mmsi,
                    COALESCE(name, '') as name,
                    1 as is_live,
                    COALESCE(CAST(updated_ms / 1000 AS INTEGER), 0) as latest_ts
                FROM vessel_latest
                WHERE (mmsi LIKE ? OR name LIKE ?) {cat_filter_latest}
            ),
            SampleMatch AS (
                SELECT
                    mmsi,
                    '' as name,
                    0 as is_live,
                    MAX(ts) as latest_ts
                FROM vessel_samples
                WHERE mmsi LIKE ?
                  AND mmsi NOT IN (SELECT mmsi FROM LatestMatch)
                  {cat_filter_samples}
                GROUP BY mmsi
            )
            SELECT mmsi, name, is_live, latest_ts FROM LatestMatch
            UNION ALL
            SELECT mmsi, name, is_live, latest_ts FROM SampleMatch
            ORDER BY name COLLATE NOCASE ASC
            LIMIT ?
        """
        params.extend([like, like, like])
        if categories:
            params.extend(categories) # For SampleMatch cat_filter
        params.append(limit)
    else:
        sql = f"""
            WITH LatestMatch AS (
                SELECT
                    mmsi,
                    COALESCE(name, '') as name,
                    1 as is_live,
                    COALESCE(CAST(updated_ms / 1000 AS INTEGER), 0) as latest_ts
                FROM vessel_latest
                WHERE 1=1 {cat_filter_latest}
            ),
            SampleMatch AS (
                SELECT
                    mmsi,
                    '' as name,
                    0 as is_live,
                    MAX(ts) as latest_ts
                FROM vessel_samples
                WHERE mmsi NOT IN (SELECT mmsi FROM LatestMatch)
                  {cat_filter_samples}
                GROUP BY mmsi
            )
            SELECT mmsi, name, is_live, latest_ts FROM LatestMatch
            UNION ALL
            SELECT mmsi, name, is_live, latest_ts FROM SampleMatch
            ORDER BY name COLLATE NOCASE ASC
            LIMIT ?
        """
        if categories:
            params.extend(categories) # For SampleMatch cat_filter
        params.append(limit)

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

def shutdown() -> None:
    """Graceful shutdown: checkpoint WAL and close all connections."""
    print("[DB] Graceful shutdown initiated...")
    db = get_db()
    try:
        with _db_lock:
            # TRUNCATE ensures WAL file is zeroed out and content moved to main DB
            print("[DB] Checkpointing WAL...")
            db.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            print("[DB] WAL checkpoint complete.")
    except Exception as e:
        print(f"[DB] Shutdown checkpoint failed: {e}")
    finally:
        if hasattr(_local, "conn"):
            _local.conn.close()
            del _local.conn
            print("[DB] Local connection closed.")

# Alusta skeema moduulin latauksen yhteydessä
# init_schema() - Removed top-level call to prevent startup crashes if DB is locked.
# It is now called explicitly in the FastAPI lifespan.

def rebuild_heatmap_cache() -> None:
    """Rebuild heatmap cache using a shadow table approach for safety and atomicity.
    
    SELECTs aggregated data into Python memory first, then INSERTs in small
    batches with commits between them so the DB write-lock is released
    periodically and snapshot/flusher writes can slip through.
    """
    if not _rebuild_lock.acquire(blocking=False):
        print("[Heatmap] Rebuild already in progress, skipping.")
        return
    
    BATCH_SIZE = 500

    try:
        now = int(time.time())
        windows = [720, 1440, 4320, 10080]  # 12h, 24h, 3d, 1w
        
        # Dedicated connection for the heavy lifting
        db = connect()
        try:
            # 1. Create shadow table
            db.execute("DROP TABLE IF EXISTS heatmap_cache_new")
            db.execute("""
                CREATE TABLE heatmap_cache_new (
                    time_window INTEGER,
                    category TEXT,
                    lat_grid REAL,
                    lon_grid REAL,
                    weight INTEGER,
                    PRIMARY KEY (time_window, category, lat_grid, lon_grid)
                )
            """)
            db.commit()

            for w in windows:
                print(f"[Heatmap] Building shadow cache for {w}m...", flush=True)
                cutoff = now - w * 60

                # Step A: SELECT into memory (read-only, no write lock)
                rows_cat = db.execute("""
                    SELECT COALESCE(vt.category, 'Other'),
                           ROUND(vs.lat, 3),
                           ROUND(vs.lon, 3),
                           COUNT(*)
                    FROM vessel_samples vs
                    JOIN vessel_latest vl ON vs.mmsi = vl.mmsi
                    LEFT JOIN vessel_types vt ON vl.type = vt.code
                    WHERE vs.ts >= ?
                    GROUP BY COALESCE(vt.category, 'Other'), ROUND(vs.lat, 3), ROUND(vs.lon, 3)
                """, (cutoff,)).fetchall()

                rows_all = db.execute("""
                    SELECT 'all',
                           ROUND(vs.lat, 3),
                           ROUND(vs.lon, 3),
                           COUNT(*)
                    FROM vessel_samples vs
                    WHERE vs.ts >= ?
                    GROUP BY ROUND(vs.lat, 3), ROUND(vs.lon, 3)
                """, (cutoff,)).fetchall()

                # Step B: INSERT in batches, committing between to yield the write lock
                all_rows = [(w, cat, lat, lon, wt) for cat, lat, lon, wt in rows_cat]
                all_rows += [(w, cat, lat, lon, wt) for cat, lat, lon, wt in rows_all]

                for i in range(0, len(all_rows), BATCH_SIZE):
                    batch = all_rows[i:i + BATCH_SIZE]
                    db.executemany("""
                        INSERT OR REPLACE INTO heatmap_cache_new
                        (time_window, category, lat_grid, lon_grid, weight)
                        VALUES (?, ?, ?, ?, ?)
                    """, batch)
                    db.commit()

            # 2. Atomic swap
            with _db_lock: # Hold main lock during the final swap
                main_db = get_db()
                main_db.execute("BEGIN TRANSACTION")
                try:
                    main_db.execute("DROP TABLE IF EXISTS heatmap_cache")
                    main_db.execute("ALTER TABLE heatmap_cache_new RENAME TO heatmap_cache")
                    main_db.commit()
                    print("[Heatmap] Cache swap complete.", flush=True)
                except Exception as e:
                    main_db.rollback()
                    print(f"[Heatmap] Cache swap failed: {e}", flush=True)
                    raise
        finally:
            db.close()
    finally:
        _rebuild_lock.release()

def query_heatmap_cache(minutes: int, category: Optional[str] = None) -> List[List[float]]:
    db = get_db()
    cat_filter = category.lower() if category and category.lower() != "all" else "all"
    
    sql = "SELECT lat_grid, lon_grid, weight FROM heatmap_cache WHERE time_window = ? AND category = ?"
    rows = db.execute(sql, (minutes, cat_filter)).fetchall()
    
    # Leaflet heat plugin format: [lat, lon, intensity]
    return [[r[0], r[1], float(r[2])] for r in rows]

def query_stats_activity(minutes_window: int) -> dict:
    """Live computation of activity stats — used as fallback and by the cache builder."""
    db = get_db()
    cutoff = int(time.time()) - (minutes_window * 60)
    
    # Query A: Timeline (aggregated to hourly buckets)
    timeline_sql = """
        SELECT (ts - ts % 3600) as hour_ts, COUNT(DISTINCT mmsi) as count
        FROM vessel_samples
        WHERE ts >= ?
        GROUP BY hour_ts
        ORDER BY hour_ts ASC
    """
    
    # Read without lock to allow concurrency during heavy MQTT writes
    tl_rows = db.execute(timeline_sql, (cutoff,)).fetchall()
    timeline = [{"ts": r[0], "count": r[1]} for r in tl_rows]
    
    # Query B: Categories
    cat_sql = """
        SELECT COALESCE(vt.category, 'Other') as category_name,
               COALESCE(vt.color, '#8899aa') as color,
               COUNT(DISTINCT vs.mmsi) as count
        FROM vessel_samples vs
        JOIN vessel_latest vl ON vs.mmsi = vl.mmsi
        LEFT JOIN vessel_types vt ON vl.type = vt.code
        WHERE vs.ts >= ?
        GROUP BY category_name, color
        ORDER BY count DESC
    """
    cat_rows = db.execute(cat_sql, (cutoff,)).fetchall()
    categories = [{"category": r[0], "color": r[1], "count": r[2]} for r in cat_rows]
    
    return {"timeline": timeline, "categories": categories}


def rebuild_trends_cache() -> None:
    """Pre-compute activity trends using a shadow table approach for safety and atomicity."""
    if not _rebuild_lock.acquire(blocking=False):
        print("[Trends] Rebuild already in progress, skipping.")
        return

    try:
        windows = [720, 1440, 4320, 10080]  # 12h, 24h, 3d, 1w
        now = int(time.time())
        db = connect()
        try:
            # 1. Create shadow table
            db.execute("DROP TABLE IF EXISTS activity_trends_cache_new")
            db.execute("""
                CREATE TABLE activity_trends_cache_new (
                    time_window INTEGER PRIMARY KEY,
                    json_blob TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)
            db.commit()

            for w in windows:
                print(f"[Trends] Building shadow cache for {w}m...", flush=True)
                data = query_stats_activity(w)
                blob = json.dumps(data, separators=(',', ':'))
                db.execute("""
                    INSERT INTO activity_trends_cache_new (time_window, json_blob, updated_at)
                    VALUES (?, ?, ?)
                """, (w, blob, now))
                db.commit()

            # 2. Atomic swap
            with _db_lock:
                main_db = get_db()
                main_db.execute("BEGIN TRANSACTION")
                try:
                    main_db.execute("DROP TABLE IF EXISTS activity_trends_cache")
                    main_db.execute("ALTER TABLE activity_trends_cache_new RENAME TO activity_trends_cache")
                    main_db.commit()
                    print("[Trends] Cache swap complete.", flush=True)
                except Exception as e:
                    main_db.rollback()
                    print(f"[Trends] Cache swap failed: {e}", flush=True)
                    raise
        finally:
            db.close()
        print("[Trends] Cache rebuild complete.", flush=True)
    finally:
        _rebuild_lock.release()


def query_trends_cache(minutes: int) -> Optional[dict]:
    """Read pre-computed trends from cache. Returns None if cache miss."""
    db = get_db()
    row = db.execute(
        "SELECT json_blob FROM activity_trends_cache WHERE time_window = ?",
        (minutes,)
    ).fetchone()
    if row:
        data = json.loads(row[0])
        # Normalize and merge "other" categories on-the-fly to handle legacy cached data
        if "categories" in data:
            merged = {}
            for c in data["categories"]:
                name = "Other" if c["category"].lower() == "other" else c["category"]
                if name in merged:
                    merged[name]["count"] += c["count"]
                else:
                    merged[name] = c
                    merged[name]["category"] = name
                    # Ensure color is standardized for "Other"
                    if name == "Other":
                        merged[name]["color"] = "#8899aa"
            data["categories"] = list(merged.values())
        return data
    return None