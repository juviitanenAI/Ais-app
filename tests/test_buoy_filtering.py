import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from app import db, state
from app.config import settings
from app.buoy_service import BuoyService
from app.ws_manager import WebSocketManager

@pytest.fixture(scope="module")
def test_db_setup():
    import os
    test_db = "test_filtering.sqlite"
    db.set_db_path(test_db)
    db.init_schema()
    yield
    if os.path.exists(test_db):
        os.remove(test_db)
    if os.path.exists(test_db + "-wal"):
        os.remove(test_db + "-wal")

@pytest.fixture(autouse=True)
def clear_state():
    with state.buoys_lock:
        state.buoys.clear()
    conn = db.get_db()
    conn.execute("DELETE FROM buoy_latest")
    conn.execute("DELETE FROM buoy_history")
    conn.commit()

def test_upsert_buoys_filtering(test_db_setup):
    now = datetime.now(timezone.utc)
    fresh_time = now.isoformat().replace("+00:00", "Z")
    stale_time = (now - timedelta(hours=25)).isoformat().replace("+00:00", "Z")
    
    features = [
        {
            "siteNumber": 1,
            "geometry": {"coordinates": [24.0, 60.0]},
            "properties": {"siteNumber": 1, "lastUpdate": fresh_time, "siteName": "Fresh"}
        },
        {
            "siteNumber": 2,
            "geometry": {"coordinates": [25.0, 61.0]},
            "properties": {"siteNumber": 2, "lastUpdate": stale_time, "siteName": "Stale"}
        }
    ]
    
    db.upsert_buoys(features, "2026-03-27T12:00:00Z", retention_minutes=1440)
    
    # Check latest
    latest = db.query_buoys()
    assert len(latest) == 1
    assert latest[0]["siteNumber"] == 1
    
    # Check history (both should be there)
    conn = db.get_db()
    history = conn.execute("SELECT site_number FROM buoy_history").fetchall()
    assert len(history) == 2

def test_prune_buoy_latest(test_db_setup):
    now = datetime.now(timezone.utc)
    fresh_time = now.isoformat().replace("+00:00", "Z")
    stale_time = (now - timedelta(hours=25)).isoformat().replace("+00:00", "Z")
    
    # Manually insert into buoy_latest to test pruning
    conn = db.get_db()
    prop_json = '{"siteNumber": 1, "test": true}'
    prop_json_stale = '{"siteNumber": 2, "test": true}'
    conn.execute("INSERT INTO buoy_latest (site_number, last_update, properties) VALUES (?, ?, ?)", (1, fresh_time, prop_json))
    conn.execute("INSERT INTO buoy_latest (site_number, last_update, properties) VALUES (?, ?, ?)", (2, stale_time, prop_json_stale))
    conn.commit()
    
    db.prune_buoy_latest(older_than_minutes=1440)
    
    latest = db.query_buoys()
    assert len(latest) == 1
    assert latest[0]["siteNumber"] == 1

@pytest.mark.anyio
async def test_buoy_service_filtering(test_db_setup):
    ws_mgr = WebSocketManager()
    loop = asyncio.get_running_loop()
    service = BuoyService(ws_mgr, loop)
    
    now = datetime.now(timezone.utc)
    fresh_time = now.isoformat().replace("+00:00", "Z")
    stale_time = (now - timedelta(hours=25)).isoformat().replace("+00:00", "Z")
    
    mock_response = {
        "dataUpdatedTime": "2026-03-27T13:00:00Z",
        "features": [
            {
                "siteNumber": 10,
                "geometry": {"coordinates": [24.0, 60.0]},
                "properties": {"siteNumber": 10, "lastUpdate": fresh_time}
            },
            {
                "siteNumber": 20,
                "geometry": {"coordinates": [25.0, 61.0]},
                "properties": {"siteNumber": 20, "lastUpdate": stale_time}
            }
        ]
    }
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(status_code=200, json=lambda: mock_response)
        await service.fetch_and_process()
        
    # Check state
    with state.buoys_lock:
        assert 10 in state.buoys
        assert 20 not in state.buoys
    
    # Check DB latest
    latest = db.query_buoys()
    assert any(b["siteNumber"] == 10 for b in latest)
    assert not any(b["siteNumber"] == 20 for b in latest)
