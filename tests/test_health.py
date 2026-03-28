import pytest
import httpx
from app.api import create_app
from app.ws_manager import WebSocketManager
from app import db

@pytest.fixture(scope="session", autouse=True)
def test_db_setup():
    import os
    test_db = "test_health.sqlite"
    db.set_db_path(test_db)
    db.init_schema()
    yield
    # Cleanup after session
    for ext in ["", "-wal", "-shm"]:
        path = test_db + ext
        if os.path.exists(path):
            os.remove(path)

@pytest.mark.anyio
async def test_up_endpoint_not_ready():
    # Mock state.is_ready to False
    from app import state
    state.is_ready = False
    
    ws_mgr = WebSocketManager()
    app = create_app(ws_mgr)
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Should return 503 when not ready
        response = await client.get("/api/up")
        assert response.status_code == 503
        
        response = await client.head("/api/up")
        assert response.status_code == 503

@pytest.mark.anyio
async def test_up_endpoint_ready():
    # Mock state.is_ready to True
    from app import state
    state.is_ready = True
    
    ws_mgr = WebSocketManager()
    app = create_app(ws_mgr)
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Should return 200 when ready
        response = await client.get("/api/up")
        assert response.status_code == 200
        
        response = await client.head("/api/up")
        assert response.status_code == 200
