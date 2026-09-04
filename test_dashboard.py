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
    assert "config_paths" in data
    assert "agycli" in data["config_paths"]
    assert "opencode" in data["config_paths"]
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


def test_add_key_missing_key():
    client = TestClient(app)
    response = client.post("/add_key", json={"provider": "openai"})
    assert response.status_code == 400
    assert response.json()["ok"] is False


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


def test_delete_key_missing_id():
    client = TestClient(app)
    response = client.post("/delete_key", json={})
    assert response.status_code == 400
    assert response.json()["ok"] is False


def test_toggle_server_json(monkeypatch):
    called = {}

    def mock_toggle(config_file, server_name, enable, command):
        called["args"] = (config_file, server_name, enable, command)
        return True

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


def test_toggle_server_missing_name():
    client = TestClient(app)
    response = client.post(
        "/toggle_server",
        json={"enable": True},
    )
    assert response.status_code == 400
    assert response.json()["ok"] is False


def test_toggle_server_failure(monkeypatch):
    monkeypatch.setattr("app.main.toggle_mcp", lambda *args, **kwargs: False)

    client = TestClient(app)
    response = client.post(
        "/toggle_server",
        json={"server_name": "failing-srv", "enable": True},
    )
    assert response.status_code == 400
    assert response.json()["ok"] is False


def test_toggle_server_label_resolution(monkeypatch):
    called = {}

    def mock_toggle(config_file, server_name, enable, command):
        called["args"] = (config_file, server_name, enable, command)
        return True

    monkeypatch.setattr("app.main.toggle_mcp", mock_toggle)

    client = TestClient(app)
    response = client.post(
        "/toggle_server",
        json={
            "server_name": "opencode-srv",
            "enable": True,
            "config_file": "opencode",
            "command": {"command": "npx"},
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    from app.main import OPENCODE_CONFIG
    assert called["args"][0] == OPENCODE_CONFIG


def test_kill_pid_endpoint():
    client = TestClient(app)
    # killing invalid pid returns 400
    res = client.post("/kill_pid", json={"pid": 99999999})
    assert res.status_code == 400
    assert res.json()["ok"] is False


def test_kill_pid_missing_pid():
    client = TestClient(app)
    res = client.post("/kill_pid", json={})
    assert res.status_code == 400
    assert res.json()["ok"] is False


def test_start_server_endpoint(monkeypatch):
    client = TestClient(app)
    # Missing command returns 400
    res = client.post("/start_server", json={})
    assert res.status_code == 400
    assert res.json()["ok"] is False

    # Start with dict command mocked
    monkeypatch.setattr("app.main.start_mcp_process", lambda cmd: 12345)
    res = client.post("/start_server", json={"command": {"command": "python", "args": ["srv.py"]}})
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["pid"] == 12345

    # Start with list command
    res = client.post("/start_server", json={"command": ["python", "srv.py"]})
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["pid"] == 12345

    # Start with string command
    res = client.post("/start_server", json={"command": "python srv.py"})
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["pid"] == 12345


def test_api_data_includes_os_processes():
    client = TestClient(app)
    res = client.get("/api/data")
    assert res.status_code == 200
    data = res.json()
    assert "os_processes" in data
    assert isinstance(data["os_processes"], list)


def test_kill_pid_invalid_pid_type():
    client = TestClient(app)
    res = client.post("/kill_pid", json={"pid": "not_an_int"})
    assert res.status_code == 400
    assert res.json()["ok"] is False
    assert res.json()["error"] == "Invalid PID"


def test_start_server_malformed_command():
    client = TestClient(app)
    res = client.post("/start_server", json={"command": 'python "unclosed quote'})
    assert res.status_code == 400
    assert res.json()["ok"] is False
    assert res.json()["error"] == "Malformed command"


def test_gather_dashboard_data_matching_and_non_string_args(monkeypatch):
    import app.main as main_mod

    mock_processes = [
        {"pid": 101, "name": "caveman-mcp", "cmd": "python /path/caveman.py", "cpu": "0.1%", "mem": "0.5%", "status": "RUNNING"},
        {"pid": 102, "name": "mcp-server", "cmd": "node /path/generic.js", "cpu": "0.2%", "mem": "0.6%", "status": "RUNNING"},
    ]
    monkeypatch.setattr(main_mod, "get_running_mcp_processes", lambda: mock_processes)

    # Mock _load_mcp_servers to return multiple servers, some with non-string args
    monkeypatch.setattr(main_mod, "_load_mcp_servers", lambda: {
        "server1": {"source": "agycli", "command": {"command": "python", "args": ["/path/caveman.py", 8080, True]}},
        "server2": {"source": "opencode", "command": {"command": "python", "args": ["/path/caveman.py"]}},  # same cmd, but PID 101 already claimed!
        "server3": {"source": "opencode", "command": {"command": "node", "args": ["/path/other.js"]}},
    })

    data = main_mod._gather_dashboard_data()
    # server1 should claim PID 101
    assert data["servers"]["server1"]["pid"] == 101
    assert data["servers"]["server1"]["is_running"] is True

    # server2 cannot claim PID 101 because server1 already claimed it
    assert data["servers"]["server2"]["pid"] is None
    assert data["servers"]["server2"]["is_running"] is False

    # server3 does not match
    assert data["servers"]["server3"]["pid"] is None
    assert data["servers"]["server3"]["is_running"] is False


