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
