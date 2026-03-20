import pytest

@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    import sqlite3
    db_file = str(tmp_path / "test_vessels.sqlite")
    
    def mock_connect():
        conn = sqlite3.connect(db_file, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    from app import db
    monkeypatch.setattr(db, "connect", mock_connect)
    
    if hasattr(db._local, "conn"):
        del db._local.conn
        
    db.init_schema()
    yield
    if hasattr(db._local, "conn"):
        db._local.conn.close()
        del db._local.conn

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
