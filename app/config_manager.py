import json
import os
import shutil
from typing import Any, Dict, Optional


def strip_jsonc_comments(text: str) -> str:
    """Strip single-line and multi-line comments and trailing commas from JSONC string."""
    result = []
    in_string = False
    escape = False
    i = 0
    n = len(text)

    while i < n:
        c = text[i]
        if in_string:
            result.append(c)
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            i += 1
        else:
            if c == '"':
                in_string = True
                result.append(c)
                i += 1
            elif c == "/" and i + 1 < n and text[i + 1] == "/":
                i += 2
                while i < n and text[i] != "\n":
                    i += 1
            elif c == "/" and i + 1 < n and text[i + 1] == "*":
                i += 2
                while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                    i += 1
                i += 2
            elif c == ",":
                # Lookahead to see if this is a trailing comma before } or ]
                j = i + 1
                is_trailing = False
                while j < n:
                    if text[j] in " \t\r\n":
                        j += 1
                    elif text[j] == "/" and j + 1 < n and text[j + 1] == "/":
                        j += 2
                        while j < n and text[j] != "\n":
                            j += 1
                    elif text[j] == "/" and j + 1 < n and text[j + 1] == "*":
                        j += 2
                        while j + 1 < n and not (text[j] == "*" and text[j + 1] == "/"):
                            j += 1
                        j += 2
                    elif text[j] in "}]":
                        is_trailing = True
                        break
                    else:
                        break
                if not is_trailing:
                    result.append(c)
                i += 1
            else:
                result.append(c)
                i += 1

    return "".join(result)


def toggle_mcp(
    config_path: str,
    mcp_name: str,
    enable: bool,
    command: Optional[Dict[str, Any]] = None,
) -> bool:
    if not os.path.exists(config_path):
        return False
    if enable and not command:
        return False

    dir_name = os.path.dirname(os.path.abspath(config_path))
    if not os.access(config_path, os.W_OK) or not os.access(dir_name, os.W_OK):
        return False

    temp_path = config_path + ".tmp"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        cleaned_content = strip_jsonc_comments(raw_content)
        data = json.loads(cleaned_content)
        if not isinstance(data, dict):
            return False

        if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
            data["mcpServers"] = {}

        if enable:
            data["mcpServers"][mcp_name] = command
        elif mcp_name in data["mcpServers"]:
            del data["mcpServers"][mcp_name]

        shutil.copy(config_path, config_path + ".bak")

        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, config_path)
        return True
    except (OSError, json.JSONDecodeError):
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        return False
