import json
import httpx
import datetime
from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from app.database import get_db_conn

async def handle_proxy(request: Request, path: str):
    # Simplistic mock: read body, forward with httpx
    body = await request.body()
    
    def fetch_key():
        with get_db_conn() as conn:
            return conn.execute("SELECT key_value, id FROM api_keys LIMIT 1").fetchone()
            
    row = await run_in_threadpool(fetch_key)
        
    if not row:
        raise HTTPException(status_code=401, detail="No API Key")
    api_key, key_id = row
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    def save_usage(tokens: int):
        date_str = datetime.datetime.utcnow().isoformat()
        with get_db_conn() as conn:
            conn.execute("INSERT INTO token_usage (key_id, tokens, date) VALUES (?, ?, ?)", (key_id, tokens, date_str))

    async def stream_generator():
        try:
            async with httpx.AsyncClient() as client:
                req = client.build_request(request.method, f"https://api.openai.com/v1/{path}", headers=headers, content=body)
                r = await client.send(req, stream=True)
                
                buffer = ""
                async for chunk in r.aiter_bytes():
                    yield chunk
                    text = chunk.decode("utf-8", errors="ignore")
                    buffer += text
                    
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                continue
                            try:
                                parsed = json.loads(data_str)
                                if "usage" in parsed and parsed["usage"]:
                                    tokens = parsed["usage"].get("total_tokens", 0)
                                    if tokens > 0:
                                        await run_in_threadpool(save_usage, tokens)
                            except json.JSONDecodeError:
                                pass
                
                # Check for single json payload (non-stream)
                buffer = buffer.strip()
                if buffer.startswith("{"):
                    try:
                        parsed = json.loads(buffer)
                        if "usage" in parsed and parsed["usage"]:
                            tokens = parsed["usage"].get("total_tokens", 0)
                            if tokens > 0:
                                await run_in_threadpool(save_usage, tokens)
                    except json.JSONDecodeError:
                        pass
                        
        except httpx.RequestError:
            yield b'{"error": {"message": "Upstream connection error"}}'
                
    return StreamingResponse(stream_generator())
