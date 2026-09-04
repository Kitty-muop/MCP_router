# AGENTS.md

## Project

MCP Manager & AI Proxy Dashboard — FastAPI app for managing API keys, MCP server configs, and proxying requests to OpenAI.

## Quick Commands

```bash
# Run dev server
uvicorn app.main:app --reload

# Run tests
pytest -v

# Run single test
pytest test_proxy.py::test_proxy_no_api_key -v
```

## Architecture

```
app/
  main.py           # FastAPI routes, template rendering
  proxy.py          # OpenAI API proxy with streaming + token tracking
  database.py       # SQLite: api_keys, token_usage tables
  config_manager.py # Toggle MCP servers in JSONC config files
  templates/        # Jinja2 HTML templates
```

## Key Paths

- **Config files managed**: `~/.config/opencode/opencode.jsonc`, `~/.gemini/config/mcp_config.json`
- **Database**: `app.db` (SQLite, auto-created on startup)
- **Config format**: JSONC (comments + trailing commas) — use `strip_jsonc_comments()` before `json.loads()`

## Conventions

- Tests use `monkeypatch` to mock DB connections to `tmp_path` — never hit real `app.db`
- Proxy always takes the **first** API key from DB (`LIMIT 1`)
- Token usage extracted from streaming SSE `data:` lines containing `usage`
- Config writes create `.bak` backup before modifying

## Gotchas

- `init_db()` runs at import time in `app/main.py` — creates `app.db` in CWD
- JSONC parsing is hand-rolled (not a library) — see `config_manager.py:strip_jsonc_comments()`
- Config toggle creates `.bak` files — clean up in tests with `tmp_path`
