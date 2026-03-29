import pytest

@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    import sqlite3
    db_file = str(tmp_path / "test_vessels.sqlite")
    cache_file = str(tmp_path / "test_cache.sqlite")
    
    def mock_connect(path):
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    from app import db
    monkeypatch.setattr(db, "connect", mock_connect)
    monkeypatch.setattr(db, "_db_path", db_file)
    monkeypatch.setattr(db, "_cache_db_path", cache_file)
    
    # Reset local connections
    for attr in ["conn", "cache_conn"]:
        if hasattr(db._local, attr):
            try:
                getattr(db._local, attr).close()
            except:
                pass
            delattr(db._local, attr)
        
    db.init_schema()
    db.init_cache_schema()
    yield
    # Cleanup
    for attr in ["conn", "cache_conn"]:
        if hasattr(db._local, attr):
            try:
                getattr(db._local, attr).close()
            except:
                pass
            delattr(db._local, attr)

def test_upsert_latest():
    from app.db import upsert_latest, get_db
    mmsi = "TEST_MMSI"
    
    upsert_latest(mmsi, loc={"lat": 60.1, "lon": 24.9, "time": 1000, "sog": 10.5, "cog": 90.0, "heading": 90.0})
    conn = get_db()
    row = conn.execute("SELECT sog, name, last_lat FROM vessel_latest WHERE mmsi=?", (mmsi,)).fetchone()
    assert row[0] == 10.5
    assert row[1] is None
    assert row[2] == 60.1
    
    upsert_latest(mmsi, meta={"name": "Test Vessel", "callSign": "CALL1", "type": 70, "destination": "HELSINKI", "timestamp": 2000})
    row2 = conn.execute("SELECT sog, name, last_lat FROM vessel_latest WHERE mmsi=?", (mmsi,)).fetchone()
    assert row2[0] == 10.5
    assert row2[1] == "Test Vessel"
    assert row2[2] == 60.1
    
    upsert_latest(mmsi, loc={"lat": 60.2, "lon": 25.0, "time": 3000, "sog": 12.0})
    row3 = conn.execute("SELECT sog, name, last_lat FROM vessel_latest WHERE mmsi=?", (mmsi,)).fetchone()
    assert row3[0] == 12.0
    assert row3[1] == "Test Vessel"
    assert row3[2] == 60.2

def test_query_vessels():
    from app.db import upsert_latest, get_db, query_vessels, insert_snapshot_rows
    import time
    
    mmsi_live = "123456789"
    mmsi_hist = "987654321"
    
    # 1. Insert live vessel
    upsert_latest(mmsi_live, meta={"name": "LIVE BOAT", "timestamp": int(time.time() * 1000)})
    
    # 2. Insert historical vessel
    ts_hist = int(time.time()) - 3600
    insert_snapshot_rows([
        (mmsi_hist, ts_hist, 60.0, 24.0, 10.0, 90.0, 90.0)
    ])
    
    # 3. Query all
    results = query_vessels(limit=10)
    assert len(results) == 2
    
    live_res = next(r for r in results if r[0] == mmsi_live)
    hist_res = next(r for r in results if r[0] == mmsi_hist)
    
    assert live_res[1] == "LIVE BOAT"
    assert live_res[2] == 1  # is_live
    assert live_res[3] >= 0
    
    assert hist_res[1] == ""
    assert hist_res[2] == 0  # is_live
    assert hist_res[3] == ts_hist
    
    # 4. Search by name
    results_name = query_vessels(q="LIVE")
    assert len(results_name) == 1
    assert results_name[0][0] == mmsi_live
    
    # 5. Search by MMSI for historical
    results_mmsi = query_vessels(q="9876")
    assert len(results_mmsi) == 1
    assert results_mmsi[0][0] == mmsi_hist

def test_prune_history():
    from app.db import insert_snapshot_rows, prune_history, get_db
    import time
    
    now = int(time.time())
    mmsi1 = "OLD_VESSEL"
    mmsi2 = "NEW_VESSEL"
    
    # 25 hours ago
    ts_old = now - (25 * 3600)
    # 1 hour ago
    ts_new = now - (1 * 3600)
    
    insert_snapshot_rows([
        (mmsi1, ts_old, 60.0, 24.0, 10.0, 90.0, 90.0),
        (mmsi2, ts_new, 60.1, 24.1, 11.0, 95.0, 95.0)
    ])
    
    # Prune older than 24 hours (1440 min)
    prune_history(older_than_minutes=24 * 60)
    
    conn = get_db()
    rows = conn.execute("SELECT mmsi FROM vessel_samples").fetchall()
    mmsis = [r[0] for r in rows]
    
    assert mmsi2 in mmsis
    assert mmsi1 not in mmsis
def test_query_vessels_with_category():
    from app.db import upsert_latest, upsert_vessel_type, query_vessels
    
    # 1. Setup vessel types
    upsert_vessel_type("70", "Cargo", "Cargo", "#4a9eff", "cargo")
    upsert_vessel_type("80", "Tanker", "Tanker", "#ff6b6b", "tanker")
    
    # 2. Insert vessels
    upsert_latest("111", meta={"name": "CARGO SHIP", "type": 70})
    upsert_latest("222", meta={"name": "TANKER SHIP", "type": 80})
    
    # 3. Query by cargo
    res_cargo = query_vessels(categories=["cargo"])
    assert len(res_cargo) == 1
    assert res_cargo[0][0] == "111"
    
    # 4. Query by tanker
    res_tanker = query_vessels(categories=["tanker"])
    assert len(res_tanker) == 1
    assert res_tanker[0][0] == "222"
    
    # 5. Query both (no category)
    res_all = query_vessels()
    assert len(res_all) == 2

def test_prune_vessel_latest():
    from app.db import upsert_latest, prune_vessel_latest, get_db
    import time
    
    # Needs to be careful with updated_ms which is set inside upsert_latest
    # We can't easily inject time.time() inside db.py without more mocking,
    # but we can wait or mock time.time in db module if needed.
    # However, upsert_latest uses time.time() * 1000.
    
    mmsi1 = "OLD_LATEST"
    mmsi2 = "NEW_LATEST"
    
    # We can't easily insert "old" updated_ms via upsert_latest because it uses time.time().
    # Let's insert manually for testing pruning logic.
    conn = get_db()
    now_ms = int(time.time() * 1000)
    old_ms = now_ms - (25 * 3600 * 1000)
    
    conn.execute("INSERT INTO vessel_latest (mmsi, updated_ms) VALUES (?, ?)", (mmsi1, old_ms))
    conn.execute("INSERT INTO vessel_latest (mmsi, updated_ms) VALUES (?, ?)", (mmsi2, now_ms))
    conn.commit()
    
    prune_vessel_latest(older_than_minutes=24 * 60)
    
    rows = conn.execute("SELECT mmsi FROM vessel_latest").fetchall()
    mmsis = [r[0] for r in rows]
    
    assert mmsi2 in mmsis
    assert mmsi2 in mmsis
    assert mmsi1 not in mmsis

def test_query_trends_cache_normalization():
    from app.db import get_cache_db, query_trends_cache
    import json
    
    conn = get_cache_db()
    # Insert legacy data with duplicate "other" categories
    legacy_data = {
        "timeline": [{"ts": 1000, "count": 10}],
        "categories": [
            {"category": "cargo", "color": "#4a9eff", "count": 10},
            {"category": "other", "color": "#808080", "count": 5},
            {"category": "Other", "color": "#8899aa", "count": 3}
        ]
    }
    conn.execute(
        "INSERT INTO activity_trends_cache (time_window, json_blob, updated_at) VALUES (?, ?, ?)",
        (1440, json.dumps(legacy_data), 1000)
    )
    conn.commit()
    
    result = query_trends_cache(1440)
    assert result is not None
    cats = result["categories"]
    
    # "other" and "Other" should be merged
    other_cat = next(c for c in cats if c["category"] == "Other")
    assert other_cat["count"] == 8
    assert other_cat["color"] == "#8899aa"
    
    # "cargo" should remain unchanged
    cargo_cat = next(c for c in cats if c["category"] == "cargo")
    assert cargo_cat["count"] == 10
    
    # Total number of categories should be 2
    assert len(cats) == 2

def test_query_vessels_case_insensitivity():
    from app.db import upsert_latest, upsert_vessel_type, query_vessels
    
    # 1. Setup vessel types with capitalized category
    upsert_vessel_type("70", "Cargo", "Cargo", "#4a9eff", "Cargo")
    upsert_vessel_type("90", "Other", "Other", "#8899aa", "Other")
    
    # 2. Insert vessels
    upsert_latest("111", meta={"name": "CARGO BOAT", "type": 70})
    upsert_latest("333", meta={"name": "OTHER BOAT", "type": 90})
    
    # 3. Query with lowercase category
    res_cargo = query_vessels(categories=["cargo"])
    assert len(res_cargo) == 1
    assert res_cargo[0][0] == "111"
    
    # 4. Query with uppercase category
    res_other = query_vessels(categories=["Other"])
    assert len(res_other) == 1
    assert res_other[0][0] == "333"
    
    # 5. Query with mixed case category
    res_other_mixed = query_vessels(categories=["oThEr"])
    assert len(res_other_mixed) == 1
    assert res_other_mixed[0][0] == "333"
