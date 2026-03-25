import pytest
import json
import asyncio
import inspect
import httpx
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.api import create_app
from app.ws_manager import WebSocketManager
from app import db, state

# Fix for Python 3.14+ deprecation warnings in FastAPI/Starlette
if not hasattr(asyncio, "_is_coroutine_patched"):
    asyncio.iscoroutinefunction = inspect.iscoroutinefunction
    asyncio._is_coroutine_patched = True

@pytest.fixture(scope="session", autouse=True)
def test_db_setup():
    import os
    test_db = "test_vessels.sqlite"
    db.set_db_path(test_db)
    db.init_schema()
    yield
    # Cleanup after session
    if os.path.exists(test_db):
        os.remove(test_db)
    if os.path.exists(test_db + "-wal"):
        os.remove(test_db + "-wal")
    if os.path.exists(test_db + "-shm"):
        os.remove(test_db + "-shm")

@pytest.fixture(autouse=True)
def clear_tables_and_state():
    # Clear memory state
    with state.buoys_lock:
        state.buoys.clear()
    
    # Clear tables
    conn = db.get_db()
    conn.execute("DELETE FROM buoy_latest")
    conn.execute("DELETE FROM buoy_history")
    conn.commit()
    yield

@pytest.fixture
def client():
    ws_mgr = WebSocketManager()
    app = create_app(ws_mgr)
    return TestClient(app)

def test_buoy_db_operations():
    test_features = [{
        "siteNumber": 123,
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [24.0, 60.0]},
        "properties": {
            "siteNumber": 123,
            "siteName": "Test Buoy",
            "siteType": "FLOATING",
            "lastUpdate": "2026-03-24T10:00:00Z",
            "temperature": 15
        }
    }]
    data_updated_time = "2026-03-24T10:05:00Z"
    
    db.upsert_buoys(test_features, data_updated_time)
    
    buoys = db.query_buoys()
    assert len(buoys) == 1
    assert buoys[0]["siteNumber"] == 123
    assert buoys[0]["name"] == "Test Buoy"
    assert buoys[0]["dataUpdatedTime"] == data_updated_time
    
    # Check history
    conn = db.get_db()
    history = conn.execute("SELECT * FROM buoy_history WHERE site_number = 123").fetchall()
    assert len(history) == 1
    assert history[0][4] == data_updated_time # data_updated_time column
    
    assert db.get_latest_buoy_update_time() == data_updated_time

@pytest.mark.anyio
async def test_buoy_service_fetching():
    ws_mgr = WebSocketManager()
    loop = asyncio.get_running_loop()
    from app.buoy_service import BuoyService
    
    service = BuoyService(ws_mgr, loop)
    
    mock_response = {
        "dataUpdatedTime": "2026-03-24T11:00:00Z",
        "features": [{
            "siteNumber": 456,
            "geometry": {"coordinates": [25.0, 61.0]},
            "properties": {"siteNumber": 456, "siteName": "Mock Buoy"}
        }]
    }
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: mock_response
        )
        
        await service.fetch_and_process()
        
        # Verify DB update
        assert db.get_latest_buoy_update_time() == "2026-03-24T11:00:00Z"
        
        # Verify State update
        with state.buoys_lock:
            assert 456 in state.buoys
            assert state.buoys[456]["data"]["siteName"] == "Mock Buoy"

@pytest.mark.anyio
async def test_api_buoys_endpoint():
    ws_mgr = WebSocketManager()
    app = create_app(ws_mgr)
    
    # Setup some state
    with state.buoys_lock:
        state.buoys[789] = {
            "lat": 62.0,
            "lon": 26.0,
            "data": {"siteNumber": 789, "siteName": "API Test Buoy"},
            "dataUpdatedTime": "2026-03-24T12:00:00Z"
        }
    
    # Use AsyncClient with transport to avoid deprecation warning
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/buoys")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        found = any(b["data"]["siteNumber"] == 789 for b in data)
        assert found
