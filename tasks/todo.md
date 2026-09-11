# Task List: MCP Port Scanner & Process Manager

## Phase 1: Foundation - Process Manager Module

### Task 1: Create `app/process_manager.py` with PID file load/save and port scanning
**Description:** Create new module with PID persistence (`~/.mcp_pids.json`) and cross-platform port scanning using psutil.
**Acceptance criteria:**
- [x] `load_pids()` reads JSON file, returns dict with opencode/agycli keys
- [x] `save_pids(data)` writes atomically (temp file + rename)
- [x] `scan_listening_ports()` returns list of dicts: {pid, port, command, user, protocol}
- [x] Handles missing psutil gracefully (fallback to `ss -tlnp` subprocess)
**Verification:**
- [x] Tests pass: `pytest test_process_manager.py::test_load_save_pids -v`
- [x] Tests pass: `pytest test_process_manager.py::test_scan_listening_ports -v`
**Dependencies:** None
**Files likely touched:** `app/process_manager.py`, `tests/test_process_manager.py`
**Estimated scope:** Medium

### Task 2: Implement MCP process matching (config command → running process)
**Description:** Match running processes to MCP server configs by comparing command lines.
**Acceptance criteria:**
- [x] `find_mcp_processes(servers, pids)` returns dict: server_name -> {pid, port, status, matched_by}
- [x] Matches by full command line (command + args) from config
- [x] Falls back to PID file if process not found but PID exists
- [x] Status values: "running", "stopped", "stale_pid"
**Verification:**
- [x] Tests pass: `pytest test_process_manager.py::test_find_mcp_processes -v`
**Dependencies:** Task 1
**Files likely touched:** `app/process_manager.py`, `tests/test_process_manager.py`
**Estimated scope:** Small

### Task 3: Implement start/stop MCP server with background process spawning
**Description:** Start MCP server as detached background process; stop by killing PID.
**Acceptance criteria:**
- [x] `start_mcp_server(config_file, server_name, command, cwd, port)` spawns `subprocess.Popen` with `start_new_session=True`
- [x] Returns {ok: true, pid, port, status: "starting"}
- [x] Saves PID + port + start_time to PID file immediately
- [x] `stop_mcp_server(server_name, config_file)` kills process group, updates PID file, returns {ok: true}
- [x] Validates command exists in config before starting
**Verification:**
- [x] Tests pass: `pytest test_process_manager.py::test_start_stop_server -v`
**Dependencies:** Task 1
**Files likely touched:** `app/process_manager.py`, `tests/test_process_manager.py`
**Estimated scope:** Medium

### Task 4: Implement health check (port listening + optional HTTP endpoint)
**Description:** After starting, verify server is healthy before marking "running".
**Acceptance criteria:**
- [x] `check_health(port, command)` waits up to 5s for port to be in LISTEN state
- [x] If command has `health_path` (e.g., "/health"), polls HTTP GET until 200 or timeout
- [x] Returns {healthy: true, latency_ms} or {healthy: false, reason}
- [x] Updates MCP process status to "running" or "failed"
**Verification:**
- [x] Tests pass: `pytest test_process_manager.py::test_health_check -v`
**Dependencies:** Task 3
**Files likely touched:** `app/process_manager.py`, `tests/test_process_manager.py`
**Estimated scope:** Small

### Task 5: Add port conflict detection and stale PID cleanup
**Description:** Detect if requested port is already in use; clean up PID file entries for dead processes.
**Acceptance criteria:**
- [x] `check_port_conflict(port, exclude_pid=None)` returns {conflict: true, pid, command} if port in use
- [x] `cleanup_stale_pids(pids, live_pids)` removes entries where PID no longer exists
- [x] Cleanup runs automatically on `scan_listening_ports()` and `find_mcp_processes()`
**Verification:**
- [x] Tests pass: `pytest test_process_manager.py::test_port_conflict -v`
- [x] Tests pass: `pytest test_process_manager.py::test_cleanup_stale_pids -v`
**Dependencies:** Task 1, Task 2
**Files likely touched:** `app/process_manager.py`, `tests/test_process_manager.py`
**Estimated scope:** Small

### Checkpoint: Foundation
- [x] All process_manager tests pass
- [x] Module imports without errors in main.py

## Phase 2: Config Manager Updates

### Task 6: Update `config_manager.py` to handle `port` field in server command
**Description:** Modify toggle_mcp to preserve/read optional port field in server command object.
**Acceptance criteria:**
- [x] `toggle_mcp` reads `port` from command dict if present
- [x] When enabling, saves port in config: `{"command": "...", "args": [...], "port": 3000}`
- [x] When disabling, preserves port in config (doesn't delete it)
- [x] Backward compatible: servers without port field still work
**Verification:**
- [x] Existing tests pass: `pytest test_config.py -v`
- [x] New test: `pytest test_config.py::test_toggle_mcp_with_port -v`
**Dependencies:** None
**Files likely touched:** `app/config_manager.py`, `tests/test_config.py`
**Estimated scope:** Small

### Task 7: Add `update_server_port` function for port changes
**Description:** New function to update just the port field of an existing MCP server.
**Acceptance criteria:**
- [x] `update_server_port(config_path, server_name, new_port)` updates port in config
- [x] Creates .bak backup before modifying
- [x] Validates new_port is int 1-65535
- [x] Returns True on success, False on failure
**Verification:**
- [x] Tests pass: `pytest test_config.py::test_update_server_port -v`
**Dependencies:** Task 6
**Files likely touched:** `app/config_manager.py`, `tests/test_config.py`
**Estimated scope:** Small

### Checkpoint: Config Updates
- [x] All config tests pass
- [x] Port field preserved through enable/disable cycles

## Phase 3: API Endpoints

### Task 8: Add `/api/ports` endpoint (all listening ports + MCP mapping)
**Description:** Return all system listening ports with MCP server association.
**Acceptance criteria:**
- [x] GET `/api/ports` returns {ports: [...], mcp_mapping: {...}}
- [x] ports: list of {pid, port, command, user, protocol, mcp_server: null|name}
- [x] mcp_mapping: server_name -> {pid, port, status}
- [x] Uses process_manager.scan_listening_ports() and find_mcp_processes()
**Verification:**
- [x] Tests pass: `pytest test_main.py::test_api_ports -v`
- [x] Manual: curl returns valid JSON with expected structure
**Dependencies:** Task 1, Task 2, Task 5
**Files likely touched:** `app/main.py`, `tests/test_main.py`
**Estimated scope:** Small

### Task 9: Add `/api/mcp_status` endpoint (current MCP process status)
**Description:** Lightweight endpoint for MCP server status (used by auto-refresh).
**Acceptance criteria:**
- [x] GET `/api/mcp_status` returns {servers: {server_name: {pid, port, status, uptime_sec}}}
- [x] Status: "running", "stopped", "starting", "failed"
- [x] uptime_sec calculated from start_time in PID file
- [x] Runs cleanup_stale_pids before returning
**Verification:**
- [x] Tests pass: `pytest test_main.py::test_api_mcp_status -v`
**Dependencies:** Task 1, Task 2, Task 5
**Files likely touched:** `app/main.py`, `tests/test_main.py`
**Estimated scope:** Small

### Task 10: Add `/start_server` endpoint (start MCP with health check)
**Description:** Start MCP server process, run health check, return final status.
**Acceptance criteria:**
- [x] POST `/start_server` {server_name, config_file} starts server via process_manager
- [x] Extracts port from config (or auto-assigns if not set)
- [x] Runs health check, waits for result
- [x] Returns {ok: true, pid, port, status: "running"|"failed", error?}
- [x] Updates PID file with result
**Verification:**
- [x] Tests pass: `pytest test_main.py::test_start_server -v`
**Dependencies:** Task 3, Task 4, Task 6
**Files likely touched:** `app/main.py`, `tests/test_main.py`
**Estimated scope:** Medium

### Task 11: Add `/stop_server` endpoint (stop MCP process, keep config)
**Description:** Stop MCP server process without removing from config.
**Acceptance criteria:**
- [x] POST `/stop_server` {server_name, config_file} stops server via process_manager
- [x] Kills process group, updates PID file status to "stopped"
- [x] Returns {ok: true}
- [x] Config entry remains (can re-enable)
**Verification:**
- [x] Tests pass: `pytest test_main.py::test_stop_server -v`
**Dependencies:** Task 3
**Files likely touched:** `app/main.py`, `tests/test_main.py`
**Estimated scope:** Small

### Task 12: Add `/update_server_port` endpoint (change port in config)
**Description:** Change port for an MCP server in config file.
**Acceptance criteria:**
- [x] POST `/update_server_port` {server_name, config_file, new_port}
- [x] Validates port not in use (via process_manager.check_port_conflict)
- [x] Calls config_manager.update_server_port
- [x] Returns {ok: true} or {ok: false, error: "Port 3000 in use by PID 1234 (other)"}
**Verification:**
- [x] Tests pass: `pytest test_main.py::test_update_server_port -v`
**Dependencies:** Task 7, Task 5
**Files likely touched:** `app/main.py`, `tests/test_main.py`
**Estimated scope:** Small

### Checkpoint: API Endpoints
- [x] All 5 new endpoints work correctly
- [x] Integration tests pass for each

## Phase 4: Dashboard UI

### Task 13: Update MCP Servers table - add Port, Status columns; replace Disable with Start/Stop/Edit Port
**Description:** Enhance existing MCP servers table with port info and action buttons.
**Acceptance criteria:**
- [x] Table columns: Name, Source, Status, Port, Command, Actions
- [x] Status badge: "Running" (green), "Stopped" (orange), "Starting" (blue), "Failed" (red)
- [x] Port column shows port number or "—" if stopped
- [x] Actions: Start (if stopped), Stop (if running), Edit Port (always)
- [x] Buttons call appropriate API endpoints
**Verification:**
- [x] Manual: Dashboard loads, table renders correctly
- [x] Manual: Click Start → status changes to Starting → Running with port
- [x] Manual: Click Stop → status changes to Stopped
**Dependencies:** Task 8, Task 9, Task 10, Task 11
**Files likely touched:** `app/templates/index.html`
**Estimated scope:** Medium

### Task 14: Add Port Scanner card (all ports table, MCP highlight, manual refresh)
**Description:** New card showing all system listening ports with MCP association highlighted.
**Acceptance criteria:**
- [x] New card "Port Scanner" after MCP Servers card
- [x] Table columns: PID, Port, Protocol, Command, User, MCP Server
- [x] MCP Server column shows badge with server name if matched, empty otherwise
- [x] "Refresh Ports" button calls `/api/ports` and updates table
- [x] Auto-refresh not enabled by default (manual only)
**Verification:**
- [x] Manual: Card displays, table populates on refresh
- [x] Manual: MCP servers highlighted correctly
**Dependencies:** Task 8
**Files likely touched:** `app/templates/index.html`
**Estimated scope:** Medium

### Task 15: Add Edit Port modal (validate port not in use)
**Description:** Modal dialog to change port for an MCP server.
**Acceptance criteria:**
- [x] Click "Edit Port" opens modal with current port pre-filled
- [x] Input validation: number 1-65535
- [x] On submit, calls `/update_server_port`
- [x] Shows error if port in use (with PID/command details)
- [x] On success, closes modal and refreshes both tables
**Verification:**
- [x] Manual: Open modal, change port, verify config updated
- [x] Manual: Try in-use port, see error message
**Dependencies:** Task 12
**Files likely touched:** `app/templates/index.html`
**Estimated scope:** Small

### Task 16: Add manual refresh buttons + auto-refresh for MCP status (30s)
**Description:** Refresh controls for both tables; auto-refresh MCP status only.
**Acceptance criteria:**
- [x] "Refresh Ports" button in Port Scanner card
- [x] "Refresh Status" button in MCP Servers card (or header)
- [x] Auto-refresh: calls `/api/mcp_status` every 30s, updates status badges/ports
- [x] Auto-refresh does NOT trigger full port scan (performance)
**Verification:**
- [x] Manual: Click refresh buttons, data updates
- [x] Manual: Wait 30s, status updates automatically
**Dependencies:** Task 9, Task 13, Task 14
**Files likely touched:** `app/templates/index.html`
**Estimated scope:** Small

### Task 17: Update JavaScript state management for new data/endpoints
**Description:** Extend STATE object and render functions for new data structures.
**Acceptance criteria:**
- [x] STATE includes ports, mcp_mapping, mcp_status
- [x] render() handles all new UI elements
- [x] fetchApi() wrapper works for all new endpoints
- [x] Error handling for all new API calls
**Verification:**
- [x] No JS console errors on dashboard load
- [x] All interactions work without errors
**Dependencies:** Task 13, Task 14, Task 15, Task 16
**Files likely touched:** `app/templates/index.html`
**Estimated scope:** Medium

### Checkpoint: UI Complete
- [x] Dashboard renders without JS errors
- [x] Start/Stop/Edit Port flows work end-to-end
- [x] Port scanner displays and refreshes correctly

## Phase 5: Tests & Polish

### Task 18: Unit tests for process_manager.py (full coverage)
**Description:** Comprehensive unit tests with mocked psutil/subprocess.
**Acceptance criteria:**
- [x] All functions covered: load/save_pids, scan_listening_ports, find_mcp_processes, start/stop_mcp_server, check_health, check_port_conflict, cleanup_stale_pids
- [x] Edge cases: missing PID file, stale PIDs, port conflicts, health check timeouts
- [x] Cross-platform paths tested (Linux/macOS)
**Verification:**
- [x] Tests pass: `pytest tests/test_process_manager.py -v`
- [x] Coverage > 90% for process_manager.py
**Dependencies:** Task 1-5
**Files likely touched:** `tests/test_process_manager.py`
**Estimated scope:** Medium

### Task 19: Integration tests for new API endpoints
**Description:** TestClient-based tests for all 5 new endpoints.
**Acceptance criteria:**
- [x] Each endpoint tested: success case, error cases, validation
- [x] Mock process_manager functions to avoid real process spawning
- [x] Test PID file persistence across requests
**Verification:**
- [x] Tests pass: `pytest tests/test_main.py -k "api_ports or mcp_status or start_server or stop_server or update_server_port" -v`
**Dependencies:** Task 8-12
**Files likely touched:** `tests/test_main.py`
**Estimated scope:** Medium

### Task 20: Test port conflict detection and resolution flow
**Description:** End-to-end test of port conflict handling.
**Acceptance criteria:**
- [x] Start server on port 3000 → success
- [x] Try start another server on port 3000 → error with PID details
- [x] Change port via Edit Port modal → success
- [x] Verify config updated correctly
**Verification:**
- [x] Tests pass: `pytest tests/test_integration_port_conflict.py -v`
**Dependencies:** Task 10, Task 12, Task 15
**Files likely touched:** `tests/test_integration_port_conflict.py`
**Estimated scope:** Small

### Task 21: Test PID persistence across server restarts
**Description:** Verify PID file survives dashboard restart.
**Acceptance criteria:**
- [x] Start server → PID file written
- [x] Restart dashboard (simulate by re-importing module)
- [x] MCP status shows server as "running" with correct PID/port
- [x] Stop server works after restart
**Verification:**
- [x] Tests pass: `pytest tests/test_pid_persistence.py -v`
**Dependencies:** Task 1, Task 3, Task 9
**Files likely touched:** `tests/test_pid_persistence.py`
**Estimated scope:** Small

### Task 22: Run full test suite, verify no regressions
**Description:** Execute all tests including existing ones.
**Acceptance criteria:**
- [x] `pytest -v` passes (all existing + new tests)
- [x] No lint errors (if lint configured)
- [x] No type errors (if typecheck configured)
**Verification:**
- [x] Full test suite passes
**Dependencies:** All previous tasks
**Files likely touched:** None (verification only)
**Estimated scope:** Small

### Checkpoint: Complete
- [x] All tests pass
- [x] No lint/type errors
- [x] Manual verification: start server → shows Running + port → stop → shows Stopped
