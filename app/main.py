from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.proxy import handle_proxy

app = FastAPI(title="MCP Manager & AI Proxy Dashboard")

templates = Jinja2Templates(directory="app/templates")

@app.post("/v1/{path:path}")
async def proxy_route(request: Request, path: str):
    return await handle_proxy(request, path)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context={"request": request}
    )

