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
async def test_up_endpoint():
    ws_mgr = WebSocketManager()
    app = create_app(ws_mgr)
    
    # Use AsyncClient with transport to avoid deprecation warning
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.head("/up")
        assert response.status_code == 200
