from fastapi import FastAPI, Request
from app.proxy import handle_proxy

app = FastAPI(title="MCP Manager & AI Proxy Dashboard")

@app.post("/v1/{path:path}")
async def proxy_route(request: Request, path: str):
    return await handle_proxy(request, path)
