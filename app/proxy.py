import httpx
from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse
from app.database import get_db_conn

async def handle_proxy(request: Request, path: str):
    # Simplistic mock: read body, forward with httpx
    body = await request.body()
    conn = get_db_conn()
    try:
        row = conn.execute("SELECT key_value, id FROM api_keys LIMIT 1").fetchone()
    finally:
        conn.close()
        
    if not row:
        raise HTTPException(status_code=401, detail="No API Key")
    api_key, key_id = row
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    async def stream_generator():
        try:
            async with httpx.AsyncClient() as client:
                req = client.build_request(request.method, f"https://api.openai.com/v1/{path}", headers=headers, content=body)
                r = await client.send(req, stream=True)
                async for chunk in r.aiter_bytes():
                    yield chunk
                    # In real code: parse chunk for usage tokens, update DB
        except httpx.RequestError:
            yield b'{"error": {"message": "Upstream connection error"}}'
                
    return StreamingResponse(stream_generator())
