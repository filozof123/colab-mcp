import os
import time
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

port = int(os.environ.get("PORT", 10000))
app = FastAPI(title="Colab MCP Bridge")

# Bekleyen ve tamamlanan görevler havuzu
TASK_QUEUE = []
COMPLETED_TASKS = {}

TOOLS_DEFINITION = [
    {
        "name": "whisper_transcribe",
        "description": "Google Drive üzerindeki ses/video dosyasını GPU ile metne dönüştürür (Whisper).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dosya_adi": {
                    "type": "string",
                    "description": "Drive içindeki ses dosyasının tam adı (örn: kayit.mp3)"
                }
            },
            "required": ["dosya_adi"]
        }
    }
]

# 1. Kök Dizin Kontrolleri
@app.get("/")
@app.head("/")
async def root():
    return {"status": "ok", "service": "Colab MCP Bridge", "queue_len": len(TASK_QUEUE)}

# 2. SSE Dinleme Kanalı
@app.head("/sse")
async def sse_head():
    return Response(status_code=200)

@app.get("/sse")
async def sse_stream(request: Request):
    async def event_generator():
        yield f"event: endpoint\ndata: /sse\n\n"
        while True:
            if await request.is_disconnected():
                break
            yield ": ping\n\n"
            import asyncio
            await asyncio.sleep(15)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

# 3. Spark MCP Protokolü
@app.post("/sse")
@app.post("/messages/")
async def handle_mcp_rpc(request: Request):
    try:
        data = await request.json()
    except Exception:
        return Response(status_code=200)

    method = data.get("method")
    req_id = data.get("id")

    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "colab-mcp-bridge", "version": "1.0.0"}
            }
        })

    elif method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS_DEFINITION}
        })

    elif method == "tools/call":
        params = data.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name == "whisper_transcribe":
            dosya = args.get("dosya_adi", "belirtilmedi")
            task_id = f"task_{int(time.time())}"
            TASK_QUEUE.append({"id": task_id, "type": "whisper", "dosya": dosya})

            result_msg = f"'{dosya}' işleme alındı (Görev ID: {task_id}). Colab GPU transkripsiyonu tamamlayıp Drive'a kaydedecektir."
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": result_msg}]}
            })

    return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": {}})

# 4. Colab Worker İletişim Uç Noktaları
@app.get("/worker/next_task")
async def get_next_task():
    if TASK_QUEUE:
        task = TASK_QUEUE.pop(0)
        return {"status": "ok", "task": task}
    return {"status": "empty"}

@app.post("/worker/complete_task")
async def complete_task(request: Request):
    data = await request.json()
    task_id = data.get("id")
    if task_id:
        COMPLETED_TASKS[task_id] = data
    return {"status": "received"}

@app.get("/.well-known/oauth-protected-resource")
@app.get("/.well-known/oauth-protected-resource/sse")
async def oauth_dummy():
    return JSONResponse({"status": "unprotected"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=port)
