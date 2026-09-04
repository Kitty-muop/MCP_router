import pathlib
import json
import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import run_in_threadpool
from app.proxy import handle_proxy
from app.database import get_db_conn
from app.config_manager import toggle_mcp, strip_jsonc_comments

app = FastAPI(title="MCP Manager & AI Proxy Dashboard")

BASE_DIR = pathlib.Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.post("/v1/{path:path}")
async def proxy_route(request: Request, path: str):
    return await handle_proxy(request, path)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    def get_keys():
        with get_db_conn() as conn:
            return conn.execute("SELECT id, provider, key_value FROM api_keys").fetchall()
    keys = await run_in_threadpool(get_keys)
    
    servers = {}
    for config_file in ["opencode.jsonc", "mcp_config.json"]:
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.loads(strip_jsonc_comments(f.read()))
                    for name, cmd in data.get("mcpServers", {}).items():
                        servers[name] = {"config_file": config_file, "command": cmd}
            except Exception:
                pass
                
    return templates.TemplateResponse(
        request=request, name="index.html", context={"request": request, "keys": keys, "servers": servers}
    )

@app.post("/add_key")
async def add_key(key: str = Form(...)):
    def insert_key():
        with get_db_conn() as conn:
            conn.execute("INSERT INTO api_keys (provider, key_value) VALUES (?, ?)", ("openai", key))
    await run_in_threadpool(insert_key)
    return RedirectResponse(url="/", status_code=303)

@app.post("/toggle_server")
async def toggle_server(server_name: str = Form(...), enable: str = Form(...), config_file: str = Form("mcp_config.json"), command: str = Form("{}")):
    is_enable = enable.lower() == "true"
    try:
        cmd_dict = json.loads(command)
    except:
        cmd_dict = {}
    await run_in_threadpool(toggle_mcp, config_file, server_name, is_enable, cmd_dict)
    return RedirectResponse(url="/", status_code=303)
