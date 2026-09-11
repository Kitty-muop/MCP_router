import json
import os
import stat
import tempfile
import pytest
from app.config_manager import toggle_mcp, update_server_port


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


def test_toggle_mcp_readonly_file(tmp_path):
    config_file = tmp_path / "readonly.json"
    config_file.write_text(json.dumps({"mcpServers": {"test": {"command": "echo"}}}))
    # Make file read-only
    os.chmod(str(config_file), stat.S_IREAD)
    bak_file = tmp_path / "readonly.json.bak"

    try:
        result = toggle_mcp(str(config_file), "test", False)
        assert result is False
        assert not bak_file.exists()
    finally:
        # Restore write permissions for cleanup
        os.chmod(str(config_file), stat.S_IWRITE | stat.S_IREAD)


def test_toggle_mcp_enable_without_command(tmp_path):
    config_file = tmp_path / "config.json"
    initial_content = json.dumps({"mcpServers": {}})
    config_file.write_text(initial_content)

    result = toggle_mcp(str(config_file), "test", True, command=None)
    assert result is False
    # File content should remain untouched
    assert config_file.read_text() == initial_content
    bak_file = tmp_path / "config.json.bak"
    assert not bak_file.exists()


def test_toggle_mcp_jsonc_support(tmp_path):
    config_file = tmp_path / "opencode.jsonc"
    jsonc_content = """{
        // OpenCode configuration comment
        /* Multi-line
           comment */
        "mcpServers": {
            "existing-mcp": {
                "command": "test-cmd",
            },
        },
    }"""
    config_file.write_text(jsonc_content)

    cmd = {"command": "python", "args": ["agent.py"]}
    result = toggle_mcp(str(config_file), "new-mcp", True, command=cmd)

    assert result is True
    data = json.loads(config_file.read_text())
    assert data["mcpServers"]["new-mcp"] == cmd
    assert data["mcpServers"]["existing-mcp"]["command"] == "test-cmd"


def test_toggle_mcp_invalid_root_type(tmp_path):
    config_file = tmp_path / "array.json"
    config_file.write_text(json.dumps(["item1", "item2"]))

    result = toggle_mcp(str(config_file), "test", False)
    assert result is False


def test_toggle_mcp_with_port(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"mcpServers": {}}))

    cmd = {"command": "node", "args": ["server.js"], "port": 3000}
    result = toggle_mcp(str(config_file), "my-server", True, command=cmd)

    assert result is True
    data = json.loads(config_file.read_text())
    assert data["mcpServers"]["my-server"]["port"] == 3000
    assert data["mcpServers"]["my-server"]["command"] == "node"


def test_update_server_port(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "mcpServers": {"my-server": {"command": "node", "args": ["s.js"], "port": 3000}}
    }))

    result = update_server_port(str(config_file), "my-server", 5000)

    assert result is True
    data = json.loads(config_file.read_text())
    assert data["mcpServers"]["my-server"]["port"] == 5000


def test_update_server_port_creates_backup(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "mcpServers": {"my-server": {"command": "node", "port": 3000}}
    }))

    update_server_port(str(config_file), "my-server", 5000)

    bak_file = tmp_path / "config.json.bak"
    assert bak_file.exists()


def test_update_server_port_invalid_port(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "mcpServers": {"my-server": {"command": "node", "port": 3000}}
    }))

    assert update_server_port(str(config_file), "my-server", 0) is False
    assert update_server_port(str(config_file), "my-server", 99999) is False
    assert update_server_port(str(config_file), "my-server", -1) is False


def test_update_server_port_nonexistent_file(tmp_path):
    result = update_server_port(str(tmp_path / "missing.json"), "srv", 3000)
    assert result is False


def test_update_server_port_server_not_found(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"mcpServers": {}}))

    result = update_server_port(str(config_file), "nonexistent", 3000)
    assert result is False
