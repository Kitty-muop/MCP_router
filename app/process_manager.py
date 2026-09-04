import os
import signal
import subprocess
import shlex
from typing import List, Dict, Any, Optional

MCP_KEYWORDS = [
    "mcp",
    "mcp_server",
    "_server",
    "caveman-mcp",
    "obsidian_server",
    "airtest_server",
    "pixon_mcp",
    "api_logger_server",
    "modelcontextprotocol",
]

def is_mcp_command(cmd: str) -> bool:
    """Return True if command string looks like an MCP server."""
    cmd_lower = cmd.lower()
    # Exclude our own monitoring app and general grep/editor commands
    if "app.main" in cmd_lower or "grep" in cmd_lower or "pytest" in cmd_lower:
        return False
    return any(keyword in cmd_lower for keyword in MCP_KEYWORDS)

def get_running_mcp_processes() -> List[Dict[str, Any]]:
    """Scan OS processes using ps and return list of running MCP servers."""
    results = []
    try:
        # ps axww -o pid,%cpu,%mem,stat,command
        out = subprocess.check_output(
            ["ps", "axww", "-o", "pid,%cpu,%mem,stat,command"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        lines = out.strip().splitlines()
        if len(lines) <= 1:
            return results

        for line in lines[1:]:
            parts = line.strip().split(None, 4)
            if len(parts) < 5:
                continue
            pid_str, cpu, mem, stat, cmd = parts
            try:
                pid = int(pid_str)
            except ValueError:
                continue

            if is_mcp_command(cmd):
                # Extract clean display name
                try:
                    cmd_parts = shlex.split(cmd) if cmd else []
                except ValueError:
                    cmd_parts = cmd.split() if cmd else []
                name = "mcp-server"
                for p in reversed(cmd_parts):
                    if p.endswith(".py") or p.endswith(".js") or "/" in p:
                        name = os.path.basename(p)
                        break
                    elif any(k in p.lower() for k in MCP_KEYWORDS):
                        name = os.path.basename(p)
                        break

                results.append({
                    "pid": pid,
                    "name": name,
                    "cmd": cmd,
                    "cpu": f"{cpu}%",
                    "mem": f"{mem}%",
                    "status": "RUNNING" if "Z" not in stat else "ZOMBIE",
                })
    except Exception:
        pass
    return results

def kill_process_by_pid(pid: int) -> bool:
    """Send SIGTERM to process PID, and SIGKILL if it does not exit."""
    if pid <= 1:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return False
    except Exception:
        return False

def start_mcp_process(command_list: List[str]) -> Optional[int]:
    """Launch detached background process for an MCP server."""
    if not command_list:
        return None
    try:
        proc = subprocess.Popen(
            command_list,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        return proc.pid
    except Exception:
        return None
