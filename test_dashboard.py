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


def test_dashboard_returns_html():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Token Router" in response.text


def test_api_data_returns_json():
    client = TestClient(app)
    response = client.get("/api/data")
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data
    assert "servers" in data
    assert "usage" in data
    assert "total_tokens" in data
    assert "total_keys" in data
    assert "total_servers" in data
    assert isinstance(data["keys"], list)
    assert isinstance(data["servers"], dict)
    assert data["total_tokens"] == 0
    assert data["total_keys"] == 0


def test_add_key_json():
    client = TestClient(app)
    response = client.post("/add_key", json={"provider": "openai", "key": "sk-test-1234"})
    assert response.status_code == 200
    assert response.json()["ok"] is True

    data = client.get("/api/data").json()
    assert data["total_keys"] == 1
    assert data["keys"][0]["provider"] == "openai"
    assert data["keys"][0]["key_value"] == "sk-test-1234"


def test_delete_key_json():
    client = TestClient(app)
    client.post("/add_key", json={"provider": "anthropic", "key": "key-test-5678"})
    data = client.get("/api/data").json()
    key_id = data["keys"][0]["id"]

    response = client.post("/delete_key", json={"key_id": key_id})
    assert response.status_code == 200
    assert response.json()["ok"] is True

    data = client.get("/api/data").json()
    assert data["total_keys"] == 0


def test_toggle_server_json(monkeypatch):
    called = {}

    def mock_toggle(config_file, server_name, enable, command):
        called["args"] = (config_file, server_name, enable, command)

    monkeypatch.setattr("app.main.toggle_mcp", mock_toggle)

    client = TestClient(app)
    response = client.post(
        "/toggle_server",
        json={
            "server_name": "test-srv",
            "enable": True,
            "config_file": "test_cfg.json",
            "command": {"command": "node", "args": ["index.js"]},
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert called["args"] == ("test_cfg.json", "test-srv", True, {"command": "node", "args": ["index.js"]})
