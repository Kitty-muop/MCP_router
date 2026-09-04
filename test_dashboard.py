import pytest
import sqlite3
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    
    def mock_get_db_conn(*args, **kwargs):
        return sqlite3.connect(db_path)
    
    import app.database as app_db
    monkeypatch.setattr(app_db, "get_db_conn", mock_get_db_conn)
    import app.main as app_main
    monkeypatch.setattr(app_main, "get_db_conn", mock_get_db_conn)
    
    import app.database as db
    db.init_db(db_path)
    yield

def test_dashboard_route():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "<title>MCP Manager</title>" in response.text
    assert "<h1>API Keys</h1>" in response.text
    assert "<h1>MCP Servers</h1>" in response.text
    assert '<form action="/add_key" method="post">' in response.text


@pytest.mark.asyncio
async def test_read_root_direct():
    from starlette.requests import Request
    from app.main import read_root

    scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
    request = Request(scope)
    response = await read_root(request)
    assert response.status_code == 200
    assert "MCP Manager" in response.body.decode()

