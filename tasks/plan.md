# Implementation Plan: MCP Port Scanner & Process Manager

## Overview
Add OS-level port scanning and MCP server process management to the existing dashboard. Users can view all system listening ports (with MCP servers highlighted), start/stop MCP server processes in the background, persist PIDs across dashboard restarts, handle port conflicts, and verify server health after startup.

## Architecture Decisions
- **New module**: `app/process_manager.py` - all process/port logic isolated here
- **PID persistence**: `~/.mcp_pids.json` stores PID, port, start time per server per config source
- **Port in config**: Optional `port` field in MCP server command object for conflict detection
- **Health checks**: After start, wait up to 5s for port listening + optional HTTP `/health` endpoint
- **Background processes**: `subprocess.Popen` with `start_new_session=True` for clean detachment
- **Cross-platform**: Use `psutil` for process/port inspection (works on Linux/macOS/Windows)

## Task List

### Phase 1: Foundation - Process Manager Module
- [x] Task 1: Create `app/process_manager.py` with PID file load/save and port scanning
- [x] Task 2: Implement MCP process matching (config command → running process)
- [x] Task 3: Implement start/stop MCP server with background process spawning
- [x] Task 4: Implement health check (port listening + optional HTTP endpoint)
- [x] Task 5: Add port conflict detection and stale PID cleanup

### Checkpoint: Foundation
- [x] Unit tests pass for process_manager.py (mocked psutil/subprocess)
- [x] Module imports without errors

### Phase 2: Config Manager Updates
- [x] Task 6: Update `config_manager.py` to handle `port` field in server command
- [x] Task 7: Add `update_server_port` function for port changes

### Checkpoint: Config Updates
- [x] Existing config tests still pass
- [x] New port handling works in toggle_mcp

### Phase 3: API Endpoints
- [x] Task 8: Add `/api/ports` endpoint (all listening ports + MCP mapping)
- [x] Task 9: Add `/api/mcp_status` endpoint (current MCP process status)
- [x] Task 10: Add `/start_server` endpoint (start MCP with health check)
- [x] Task 11: Add `/stop_server` endpoint (stop MCP process, keep config)
- [x] Task 12: Add `/update_server_port` endpoint (change port in config)

### Checkpoint: API Endpoints
- [x] All new endpoints return correct JSON structure
- [x] Integration tests pass for each endpoint

### Phase 4: Dashboard UI
- [x] Task 13: Update MCP Servers table - add Port, Status columns; replace Disable with Start/Stop/Edit Port
- [x] Task 14: Add Port Scanner card (all ports table, MCP highlight, manual refresh)
- [x] Task 15: Add Edit Port modal (validate port not in use)
- [x] Task 16: Add manual refresh buttons + auto-refresh for MCP status (30s)
- [x] Task 17: Update JavaScript state management for new data/endpoints

### Checkpoint: UI Complete
- [x] Dashboard renders without JS errors
- [x] Start/Stop/Edit Port flows work end-to-end
- [x] Port scanner displays and refreshes correctly

### Phase 5: Tests & Polish
- [x] Task 18: Unit tests for process_manager.py (full coverage)
- [x] Task 19: Integration tests for new API endpoints
- [x] Task 20: Test port conflict detection and resolution flow
- [x] Task 21: Test PID persistence across server restarts
- [x] Task 22: Run full test suite, verify no regressions

### Checkpoint: Complete
- [x] All tests pass
- [x] No lint/type errors
- [x] Manual verification: start server → shows Running + port → stop → shows Stopped

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| psutil not available on all platforms | Medium | Graceful fallback to `ss`/`lsof` subprocess; document requirement |
| Process orphaning on dashboard crash | Medium | `start_new_session=True` + PID file cleanup on startup |
| Port race condition (check-then-act) | Low | Bind attempt in start_server catches actual conflict |
| Health check false negatives | Low | Configurable timeout, fallback to port-only check |
| Config JSONC comments lost on port update | Medium | Preserve original formatting in config_manager |

## Open Questions
- None - all decisions resolved in interview
