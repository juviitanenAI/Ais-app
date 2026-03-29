import pytest
import threading
import time
from app import db, state

@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    import sqlite3
    db_file = str(tmp_path / "test_concurrency.sqlite")
    cache_file = str(tmp_path / "test_cache.sqlite")

    def mock_connect(path):
        # Using timeout to ensure we don't hang if there's a real deadlock
        conn = sqlite3.connect(path, check_same_thread=False, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    monkeypatch.setattr(db, "connect", mock_connect)
    monkeypatch.setattr(db, "_db_path", db_file)
    monkeypatch.setattr(db, "_cache_db_path", cache_file)

    # Reset local connections
    for attr in ["conn", "cache_conn"]:
        if hasattr(db._local, attr):
            getattr(db._local, attr).close()
            delattr(db._local, attr)

    db.init_schema()
    db.init_cache_schema()
    yield
    for attr in ["conn", "cache_conn"]:
        if hasattr(db._local, attr):
            getattr(db._local, attr).close()
            delattr(db._local, attr)

def test_cache_rebuild_does_not_block_writes():
    """
    Test that long-running cache rebuild does not block concurrent writes to vessel_latest.
    This simulates the MQTT ingest / flusher task running while a heatmap is building.
    """
    from app.db import rebuild_heatmap_cache, upsert_latest, get_db
    
    # 1. Add some sample data so the rebuild has something to do
    for i in range(100):
        db.insert_snapshot_rows([
            (f"MMSI_{i}", int(time.time()) - 100, 60.0, 24.0, 10.0, 0, 0)
        ])
    
    # 2. Start a cache rebuild in a background thread
    # We'll use a wrapper to track if it's running
    rebuild_started = threading.Event()
    rebuild_finished = threading.Event()
    
    def run_rebuild():
        rebuild_started.set()
        rebuild_heatmap_cache()
        rebuild_finished.set()

    thread = threading.Thread(target=run_rebuild)
    thread.start()
    
    rebuild_started.wait(timeout=2)
    
    # 3. While it's running, try to perform a write that requires _db_lock
    # If the rebuild was holding _db_lock, this would block or fail
    write_success = False
    try:
        # We try multiple times in case the rebuild hasn't hit the heavy parts yet
        for i in range(5):
            upsert_latest("WRITE_TEST", loc={"lat": 1.0, "lon": 1.0, "time": int(time.time())})
            time.sleep(0.1)
        write_success = True
    except Exception as e:
        print(f"Write failed: {e}")
    
    # 4. Cleanup
    thread.join(timeout=10)
    
    assert write_success, "Writes should succeed while cache rebuild is in progress"
    
    # Verify the write actually happened
    conn = get_db()
    row = conn.execute("SELECT mmsi FROM vessel_latest WHERE mmsi='WRITE_TEST'").fetchone()
    assert row is not None
    assert row[0] == "WRITE_TEST"
