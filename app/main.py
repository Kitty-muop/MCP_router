import pathlib
import json
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import run_in_threadpool
from app.proxy import handle_proxy
from app.database import get_db_conn, init_db
from app.config_manager import toggle_mcp, strip_jsonc_comments

app = FastAPI(title="MCP Manager & AI Proxy Dashboard")
init_db()

BASE_DIR = pathlib.Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

OPENCODE_CONFIG = os.path.expanduser("~/.config/opencode/opencode.jsonc")
AGYCLI_CONFIG = os.path.expanduser("~/.gemini/config/mcp_config.json")


def _gather_dashboard_data() -> dict:
    """Collect keys, usage, and servers for both HTML and JSON views."""
    with get_db_conn() as conn:
        raw_keys = conn.execute("SELECT id, provider, key_value FROM api_keys").fetchall()
        raw_usage = conn.execute(
            "SELECT a.provider, a.key_value, COALESCE(SUM(t.tokens),0) as total "
            "FROM api_keys a LEFT JOIN token_usage t ON a.id = t.key_id "
            "GROUP BY a.id"
        ).fetchall()

    keys = [{"id": r[0], "provider": r[1], "key_value": r[2]} for r in raw_keys]
    usage = [{"provider": r[0], "key_value": r[1], "total_tokens": r[2]} for r in raw_usage]

    servers = {}
    for label, config_file in [("opencode", OPENCODE_CONFIG), ("agycli", AGYCLI_CONFIG)]:
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.loads(strip_jsonc_comments(f.read()))
                    for name, cmd in data.get("mcpServers", {}).items():
                        servers[name] = {"config_file": config_file, "source": label, "command": cmd}
            except Exception:
                pass

    return {
        "keys": keys,
        "servers": servers,
        "usage": usage,
        "total_tokens": sum(u["total_tokens"] for u in usage),
        "total_keys": len(keys),
        "total_servers": len(servers),
        "config_paths": {"agycli": AGYCLI_CONFIG, "opencode": OPENCODE_CONFIG},
    }


@app.post("/v1/{path:path}")
async def proxy_route(request: Request, path: str):
    return await handle_proxy(request, path)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    data = await run_in_threadpool(_gather_dashboard_data)
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"request": request, **data},
    )


@app.get("/api/data")
async def api_data():
    data = await run_in_threadpool(_gather_dashboard_data)
    return JSONResponse(data)


@app.post("/add_key")
async def add_key(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON"}, status_code=400)

    provider = body.get("provider", "openai")
    key = body.get("key")
    if not key:
        return JSONResponse({"ok": False, "error": "key is required"}, status_code=400)

    def insert_key():
        with get_db_conn() as conn:
            conn.execute("INSERT INTO api_keys (provider, key_value) VALUES (?, ?)", (provider, key))
    await run_in_threadpool(insert_key)
    return JSONResponse({"ok": True})


@app.post("/delete_key")
async def delete_key(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON"}, status_code=400)

    key_id = body.get("key_id")
    if key_id is None:
        return JSONResponse({"ok": False, "error": "key_id is required"}, status_code=400)

    def remove_key():
        with get_db_conn() as conn:
            conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
    await run_in_threadpool(remove_key)
    return JSONResponse({"ok": True})


@app.post("/toggle_server")
async def toggle_server(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON"}, status_code=400)

    server_name = body.get("server_name")
    if not server_name:
        return JSONResponse({"ok": False, "error": "server_name is required"}, status_code=400)

    enable = body.get("enable", False)
    config_file = body.get("config_file", AGYCLI_CONFIG)
    if config_file == "agycli":
        config_file = AGYCLI_CONFIG
    elif config_file == "opencode":
        config_file = OPENCODE_CONFIG
    elif config_file:
        config_file = os.path.expanduser(config_file)
    command = body.get("command", {})

    ok = await run_in_threadpool(toggle_mcp, config_file, server_name, enable, command)
    return JSONResponse({"ok": bool(ok)}, status_code=200 if ok else 400)
