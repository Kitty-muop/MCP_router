import pytest
from fastapi.testclient import TestClient
import sqlite3
import httpx

@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    
    # Patch get_db_conn to use the temp db
    def mock_get_db_conn(*args, **kwargs):
        return sqlite3.connect(db_path)
    
    import app.database as app_db
    monkeypatch.setattr(app_db, "get_db_conn", mock_get_db_conn)
    import app.proxy as app_proxy
    monkeypatch.setattr(app_proxy, "get_db_conn", mock_get_db_conn)
    
    # Initialize the temp db
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE IF NOT EXISTS api_keys (id INTEGER PRIMARY KEY, provider TEXT, key_value TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS token_usage (id INTEGER PRIMARY KEY, key_id INTEGER, tokens INTEGER, date TEXT)")
    conn.commit()
    conn.close()
    yield

def test_proxy_no_api_key():
    from app.main import app as fastapi_app
    client = TestClient(fastapi_app)
    response = client.post("/v1/chat/completions", json={"test": "data"})
    assert response.status_code == 401
    assert response.json() == {"detail": "No API Key"}

def test_proxy_with_api_key(monkeypatch):
    from app.main import app as fastapi_app
    import app.database as app_db
    import app.proxy as app_proxy
    
    conn = app_db.get_db_conn()
    conn.execute("INSERT INTO api_keys (key_value) VALUES ('sk-test-key')")
    conn.commit()

    class MockResponse:
        async def aiter_bytes(self):
            yield b"data: test chunk\n\n"
    
    class MockClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        def build_request(self, method, url, headers, content):
            return "mock_request"
        async def send(self, req, stream=False):
            return MockResponse()

    monkeypatch.setattr(app_proxy.httpx, "AsyncClient", MockClient)

    client = TestClient(fastapi_app)
    response = client.post("/v1/chat/completions", json={"test": "data"})
    assert response.status_code == 200
    assert response.text == "data: test chunk\n\n"
