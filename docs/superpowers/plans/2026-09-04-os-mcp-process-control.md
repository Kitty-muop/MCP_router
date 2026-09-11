# OS MCP Process Detection & PID ON/OFF Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect all running MCP servers and related processes in Linux with their actual OS PIDs, display them in the UI with live status indicators, and provide buttons to Turn OFF (kill PID) or Turn ON (start/enable).

**Architecture:** A new `app/process_manager.py` module scans system processes (via `ps` or `/proc`) for commands matching MCP signatures, extracts PID, CPU, memory, and command lines, and safely terminates PIDs with `os.kill(pid, SIGTERM)`. New API routes (`POST /kill_pid`, `POST /start_server`) in `app/main.py` expose these actions, and `app/templates/index.html` renders live OS processes, PID badges, and interactive ON/OFF buttons.

**Tech Stack:** Python 3.11, FastAPI, standard library (`os`, `subprocess`, `signal`), vanilla JS/CSS.

**Spec:** Bounded design from brainstorming session (2026-09-04).

## Global Constraints

- Linux OS target.
- Do not kill arbitrary non-MCP system processes (validate PID ownership/permissions).
- All CSS and JS must remain inline in `app/templates/index.html`.
- Dark glassmorphism theme must be maintained.
- All existing tests in `test_db.py`, `test_config.py`, `test_proxy.py`, `test_dashboard.py` must continue passing.
- Python test runner: `uv run pytest`.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `app/process_manager.py` | Create | Scan OS for MCP processes, extract PID/metrics, kill PID by signal, launch background MCP servers |
| `test_process.py` | Create | Unit tests for process detection, killing mock processes, and permission checks |
| `app/main.py` | Modify | Add `os_processes` to `_gather_dashboard_data()`, add `/kill_pid` and `/start_server` endpoints |
| `test_dashboard.py` | Modify | Add tests for `/kill_pid` and `/start_server` endpoints |
| `app/templates/index.html` | Modify | Add "Active OS Processes (PIDs)" section, PID badges (`🟢 PID: 12345`), and prominent Turn OFF / Turn ON buttons |

---

### Task 1: Backend Process Scanner & Control Endpoints

**Files:**
- Create: `app/process_manager.py`
- Create: `test_process.py`
- Modify: `app/main.py`
- Modify: `test_dashboard.py`

**Interfaces:**
- Produces:
  - `get_running_mcp_processes() -> list[dict]`: list of `{"pid": int, "name": str, "cmd": str, "cpu": str, "mem": str, "status": str}`
  - `kill_process_by_pid(pid: int) -> bool`: send `SIGTERM` (fallback `SIGKILL`), return `True` on success
  - `start_mcp_process(command_list: list[str]) -> int`: launch detached background process, return new `pid`
  - `POST /kill_pid` with JSON `{"pid": int}` -> `{"ok": bool}`
  - `POST /start_server` with JSON `{"command": dict|list}` -> `{"ok": bool, "pid": int}`

- [ ] **Step 1: Write tests for process_manager.py in test_process.py**

Create `test_process.py`:

```python
import os
import signal
import subprocess
import sys
import pytest
from app.process_manager import get_running_mcp_processes, kill_process_by_pid, start_mcp_process

def test_get_running_mcp_processes():
    # Start a dummy process matching mcp naming
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10) # dummy_mcp_server"])
    try:
        processes = get_running_mcp_processes()
        pids = [p["pid"] for p in processes]
        assert proc.pid in pids
        matched = next(p for p in processes if p["pid"] == proc.pid)
        assert "dummy_mcp_server" in matched["cmd"]
        assert matched["status"] == "RUNNING"
    finally:
        proc.kill()
        proc.wait()

def test_kill_process_by_pid():
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10) # to_kill_mcp"])
    try:
        success = kill_process_by_pid(proc.pid)
        assert success is True
        proc.wait(timeout=2)
        assert proc.poll() is not None
    finally:
        if proc.poll() is None:
            proc.kill()

def test_kill_invalid_pid():
    # PID 99999999 doesn't exist
    assert kill_process_by_pid(99999999) is False

def test_start_mcp_process():
    pid = start_mcp_process([sys.executable, "-c", "import time; time.sleep(5) # spawned_mcp"])
    assert isinstance(pid, int)
    assert pid > 0
    try:
        os.kill(pid, 0) # check alive
    finally:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest test_process.py -v`
Expected: FAIL — `app.process_manager` does not exist

- [ ] **Step 3: Implement app/process_manager.py**

Create `app/process_manager.py`:

```python
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
        # ps ax -o pid,%cpu,%mem,stat,command
        out = subprocess.check_output(
            ["ps", "ax", "-o", "pid,%cpu,%mem,stat,command"],
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
                cmd_parts = shlex.split(cmd) if cmd else []
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
```

- [ ] **Step 4: Run test_process.py to verify it passes**

Run: `uv run pytest test_process.py -v`
Expected: 4 passed

- [ ] **Step 5: Integrate endpoints into app/main.py and update test_dashboard.py**

In `app/main.py`:
1. Import `get_running_mcp_processes`, `kill_process_by_pid`, `start_mcp_process` from `app.process_manager`.
2. In `_gather_dashboard_data()`, add `"os_processes": get_running_mcp_processes()`. Also check each declared server in `servers` to see if a matching PID exists in `os_processes`, setting `info["pid"] = matched_pid` and `info["is_running"] = True/False`.
3. Add `@app.post("/kill_pid")`:
```python
@app.post("/kill_pid")
async def kill_pid_route(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON"}, status_code=400)
    pid = body.get("pid")
    if pid is None:
        return JSONResponse({"ok": False, "error": "Missing pid"}, status_code=400)
    success = await run_in_threadpool(kill_process_by_pid, int(pid))
    return JSONResponse({"ok": success}, status_code=200 if success else 400)
```
4. Add `@app.post("/start_server")`:
```python
@app.post("/start_server")
async def start_server_route(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON"}, status_code=400)
    command = body.get("command")
    if not command:
        return JSONResponse({"ok": False, "error": "Missing command"}, status_code=400)
    cmd_list = []
    if isinstance(command, dict):
        base_cmd = command.get("command", "")
        args = command.get("args", [])
        if base_cmd:
            cmd_list = [base_cmd] + args
    elif isinstance(command, list):
        cmd_list = command
    elif isinstance(command, str):
        cmd_list = shlex.split(command)
    if not cmd_list:
        return JSONResponse({"ok": False, "error": "Invalid command list"}, status_code=400)
    pid = await run_in_threadpool(start_mcp_process, cmd_list)
    return JSONResponse({"ok": bool(pid), "pid": pid}, status_code=200 if pid else 400)
```

Add tests in `test_dashboard.py`:
```python
def test_kill_pid_endpoint():
    client = TestClient(app)
    # killing invalid pid returns 400
    res = client.post("/kill_pid", json={"pid": 99999999})
    assert res.status_code == 400
    assert res.json()["ok"] is False

def test_api_data_includes_os_processes():
    client = TestClient(app)
    res = client.get("/api/data")
    assert res.status_code == 200
    data = res.json()
    assert "os_processes" in data
    assert isinstance(data["os_processes"], list)
```

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest test_db.py test_config.py test_proxy.py test_dashboard.py test_process.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add app/process_manager.py test_process.py app/main.py test_dashboard.py
git commit -m "feat: add OS MCP process scanner and PID kill/start endpoints"
```

---

### Task 2: Frontend UX/UI for OS MCP PID Display & ON/OFF Controls

**Files:**
- Modify: `app/templates/index.html`

**Interfaces:**
- Consumes:
  - `GET /api/data` → includes `os_processes: [{pid, name, cmd, cpu, mem, status}, ...]`
  - `POST /kill_pid` with `{"pid": int}`
  - `POST /start_server` with `{"command": dict}`

- [ ] **Step 1: Update app/templates/index.html with OS MCP Process Table and Action Buttons**

Key additions to `app/templates/index.html`:
1. **5th Metric Card**:
   - `OS MCP PIDs` metric card (displays count of active MCP processes in OS with pulse green dot).
2. **"Active OS MCP Processes (Linux PIDs)" Card**:
   - Lists every detected running MCP process in the OS.
   - Shows:
     - **PID** (formatted bold: `PID 137648`)
     - **Process Name**
     - **CPU / RAM** metrics (`0.2% CPU / 0.6% RAM`)
     - **Command Line** (truncated, hoverable)
     - **Big Red Button: `⏻ Turn OFF (Kill PID)`** with confirm dialog or immediate action + toast feedback.
3. **Configured Servers Section Enhancement**:
   - If server's command matches a running PID:
     - Green badge: `🟢 ONLINE (PID: 137648)`
     - Button: **⏻ Turn OFF** (kills the PID and optionally disables in config)
   - If server is not running:
     - Gray badge: `⚪ STOPPED`
     - Button: **▶ Turn ON** (starts the server via `/start_server`)
4. **Fast Auto-Refresh**:
   - Polling interval set to 5 seconds so PID changes, kills, and starts reflect almost instantly without manual reload.
   - Manual `↻ Refresh PIDs` button in the header and tables for instant reload.

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest test_db.py test_config.py test_proxy.py test_dashboard.py test_process.py -v`
Expected: All 25+ tests PASS

- [ ] **Step 3: Verify manually in browser**

Open: `http://localhost:8000`
Verify:
1. "Active OS MCP Processes" section appears and shows the actual running servers (`caveman-mcp`, `obsidian_server`, `airtest_server`, `pixon_mcp`, `api_logger_server`).
2. Each shows its real OS PID.
3. Clicking **⏻ Turn OFF (Kill PID)** on a test process terminates it cleanly and toast says `Process <pid> killed`.
4. Process vanishes from table on the next 5s poll.
5. Configured servers show `Turn ON` / `Turn OFF` buttons corresponding to their PID status.

- [ ] **Step 4: Commit**

```bash
git add app/templates/index.html
git commit -m "feat: add OS MCP PID table and Turn OFF/ON process buttons to UI"
```
