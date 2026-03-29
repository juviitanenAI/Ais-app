import pytest
import threading
import time
import sqlite3
from unittest.mock import patch, MagicMock
from app import db

@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    import sqlite3
    db_file = str(tmp_path / "test_safety.sqlite")
    cache_file = str(tmp_path / "test_cache.sqlite")
    
    def mock_connect(path):
        conn = sqlite3.connect(path, check_same_thread=False, timeout=5)
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
            getattr(db._local, attr).close()
            delattr(db._local, attr)
        
    db.init_schema()
    db.init_cache_schema()
    yield
    for attr in ["conn", "cache_conn"]:
        if hasattr(db._local, attr):
            getattr(db._local, attr).close()
            delattr(db._local, attr)

def test_rebuild_concurrency_lock():
    """Verify that multiple concurrent calls to rebuild_heatmap_cache skip if already running."""
    from app.db import _rebuild_lock, rebuild_heatmap_cache
    
    # We'll lock it in a SEPARATE thread so it's not re-entrant
    locked_event = threading.Event()
    stop_event = threading.Event()

    def hold_lock():
        with _rebuild_lock:
            locked_event.set()
            stop_event.wait(timeout=10)

    t = threading.Thread(target=hold_lock)
    t.start()
    
    try:
        locked_event.wait(timeout=2)
        assert _rebuild_lock.locked()
        
        # This should now raise AlreadyRebuildingError because of the lock held by the other thread
        from app.db import AlreadyRebuildingError
        with pytest.raises(AlreadyRebuildingError):
            rebuild_heatmap_cache()
    finally:
        stop_event.set()
        t.join()

def test_heatmap_rebuild_atomicity():
    """Verify that the ancient heatmap_cache is still readable while a new one is being built."""
    from app.db import get_cache_db, rebuild_heatmap_cache
    
    conn = get_cache_db()
    # 1. Seat some initial data
    conn.execute("INSERT INTO heatmap_cache (time_window, category, lat_grid, lon_grid, weight) VALUES (720, 'all', 1.0, 1.0, 10)")
    conn.commit()
    
    # 2. Add some samples so the rebuild has work to do
    db.insert_snapshot_rows([
        ("MMSI_1", int(time.time()) - 100, 60.0, 24.0, 10.0, 0, 0)
    ])
    
    # 3. Simulate a slow rebuild
    # We'll use a Thread to run the rebuild and check from main thread
    rebuild_started = threading.Event()
    rebuild_finished = threading.Event()
    
    def run_rebuild():
        rebuild_started.set()
        rebuild_heatmap_cache()
        rebuild_finished.set()

    thread = threading.Thread(target=run_rebuild)
    thread.start()
    
    rebuild_started.wait(timeout=2)
    
    # While it's running, check if old data is still there
    try:
        if not rebuild_finished.is_set():
            rows = conn.execute("SELECT weight FROM heatmap_cache WHERE lat_grid=1.0").fetchone()
            assert rows is not None, "Heatmap cache should not be dropped until rebuilding is complete"
            assert rows[0] == 10
    finally:
        thread.join()

def test_rebuild_cleanup_on_failure():
    """Verify that heatmap_cache is NOT dropped if the rebuild fails before the swap."""
    from app.db import get_cache_db, rebuild_heatmap_cache
    import sqlite3
    
    original_conn = get_cache_db()
    original_conn.execute("INSERT INTO heatmap_cache (time_window, category, lat_grid, lon_grid, weight) VALUES (720, 'all', 2.0, 2.0, 20)")
    original_conn.commit()
    
    # To mock a failure during execution, we'll mock 'connect' 
    # so that any attempt to open a NEW connection inside the rebuild fails.
    
    original_connect = db.connect
    def mock_fail_connect(path):
        raise sqlite3.OperationalError("Simulated Connection Failure")
    
    with patch('app.db.connect', side_effect=mock_fail_connect):
        try:
            rebuild_heatmap_cache()
        except sqlite3.OperationalError:
            pass
            
    # Original table should still be intact in the REAL db
    row = original_conn.execute("SELECT weight FROM heatmap_cache WHERE lat_grid=2.0").fetchone()
    assert row is not None
    assert row[0] == 20
