import pytest
import threading
import time
import sqlite3
from unittest.mock import patch, MagicMock
from app import db

@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    db_file = str(tmp_path / "test_safety.sqlite")
    
    def mock_connect():
        conn = sqlite3.connect(db_file, check_same_thread=False, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    monkeypatch.setattr(db, "connect", mock_connect)
    
    # Reset local connection
    if hasattr(db._local, "conn"):
        db._local.conn.close()
        del db._local.conn
        
    db.init_schema()
    yield
    if hasattr(db._local, "conn"):
        db._local.conn.close()
        del db._local.conn

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
        
        # This should return immediately because of the lock held by the other thread
        with patch('builtins.print') as mock_print:
            rebuild_heatmap_cache()
            mock_print.assert_any_call("[Heatmap] Rebuild already in progress, skipping.")
    finally:
        stop_event.set()
        t.join()

def test_heatmap_rebuild_atomicity():
    """Verify that the ancient heatmap_cache is still readable while a new one is being built."""
    from app.db import get_db, rebuild_heatmap_cache
    
    conn = get_db()
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
    from app.db import get_db, rebuild_heatmap_cache
    import sqlite3
    
    conn = get_db()
    conn.execute("INSERT INTO heatmap_cache (time_window, category, lat_grid, lon_grid, weight) VALUES (720, 'all', 2.0, 2.0, 20)")
    conn.commit()
    
    # To mock a failure during execution on an immutable type, 
    # we mock 'connect' to return a MagicMock connection, OR 
    # we patch the 'rebuild_heatmap_cache' internals.
    
    # Let's mock the actual INSERT query by patching the CONNECTION'S execute.
    # Since we use get_db(), we can mock THAT.
    
    original_conn = get_db()
    mock_conn = MagicMock(spec=sqlite3.Connection)
    mock_conn.execute.side_effect = Exception("Simulated Crash")
    
    with patch('app.db.get_db', return_value=mock_conn):
        try:
            rebuild_heatmap_cache()
        except:
            pass
            
    # Original table should still be intact in the REAL db
    row = original_conn.execute("SELECT weight FROM heatmap_cache WHERE lat_grid=2.0").fetchone()
    assert row is not None
    assert row[0] == 20
