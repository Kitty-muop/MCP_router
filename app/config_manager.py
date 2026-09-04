import json
import os
import shutil
from typing import Any, Dict, Optional


def toggle_mcp(
    config_path: str,
    mcp_name: str,
    enable: bool,
    command: Optional[Dict[str, Any]] = None,
) -> bool:
    if not os.path.exists(config_path):
        return False
    shutil.copy(config_path, config_path + ".bak")
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
        data["mcpServers"] = {}
    if enable and command:
        data["mcpServers"][mcp_name] = command
    elif not enable and mcp_name in data["mcpServers"]:
        del data["mcpServers"][mcp_name]
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return True
