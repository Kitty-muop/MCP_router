import json
import os
import tempfile
import pytest
from app.config_manager import toggle_mcp


def test_toggle_mcp():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        json.dump({"mcpServers": {"test-mcp": {"command": "echo"}}}, f)
        path = f.name
    try:
        result = toggle_mcp(path, "test-mcp", False)
        assert result is True
        with open(path) as f:
            data = json.load(f)
            assert "test-mcp" not in data.get("mcpServers", {})
    finally:
        if os.path.exists(path):
            os.remove(path)
        if os.path.exists(path + ".bak"):
            os.remove(path + ".bak")


def test_toggle_mcp_enable(tmp_path):
    config_file = tmp_path / "config.json"
    initial_data = {"mcpServers": {}}
    config_file.write_text(json.dumps(initial_data))

    cmd = {"command": "node", "args": ["server.js"]}
    result = toggle_mcp(str(config_file), "my-mcp", True, command=cmd)

    assert result is True
    data = json.loads(config_file.read_text())
    assert data["mcpServers"]["my-mcp"] == cmd


def test_toggle_mcp_creates_backup(tmp_path):
    config_file = tmp_path / "config.json"
    initial_data = {"mcpServers": {"old": {"command": "test"}}}
    config_file.write_text(json.dumps(initial_data))

    toggle_mcp(str(config_file), "old", False)

    bak_file = tmp_path / "config.json.bak"
    assert bak_file.exists()
    bak_data = json.loads(bak_file.read_text())
    assert "old" in bak_data["mcpServers"]


def test_toggle_mcp_nonexistent_file(tmp_path):
    non_existent = tmp_path / "does_not_exist.json"
    result = toggle_mcp(str(non_existent), "any-mcp", False)
    assert result is False


def test_toggle_mcp_missing_mcpservers_key(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"otherKey": 123}))

    cmd = {"command": "python", "args": ["mcp.py"]}
    result = toggle_mcp(str(config_file), "new-mcp", True, command=cmd)

    assert result is True
    data = json.loads(config_file.read_text())
    assert data["mcpServers"]["new-mcp"] == cmd
    assert data["otherKey"] == 123
