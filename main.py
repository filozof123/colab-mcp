import os
import json
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

port = int(os.environ.get("PORT", 10000))
app = FastAPI(title="Colab MCP Bridge")

# Spark / Gemini'nin tanıyacağı araç listesi
TOOLS_DEFINITION = [
    {
        "name": "whisper_transcribe",
        "description": "Google Drive üzerindeki ses/video dosyasını GPU kullanarak metne dönüştürür (Whisper).",
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
    return {"status": "ok", "service": "Colab MCP Bridge"}

# 2. SSE Dinleme Kanalı (GET & HEAD)
@app.head("/sse")
async def sse_head():
    return Response(status_code=200)

@app.get("/sse")
async def sse_stream(request: Request):
    async def event_generator():
        # MCP SSE protokolü: Spark'a mesaj gönderebileceği uç noktayı bildir
        yield f"event: endpoint\ndata: /sse\n\n"
        # Bağlantıyı canlı tutan periyodik ping
        while True:
            if await request.is_disconnected():
                break
            yield ": ping\n\n"
            import asyncio
            await asyncio.sleep(15)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# 3. Spark'ın El Sıkışma ve Araç İstekleri (POST /sse)
@app.post("/sse")
@app.post("/messages/")
async def handle_mcp_rpc(request: Request):
    try:
        data = await request.json()
    except Exception:
        return Response(status_code=200)

    method = data.get("method")
    req_id = data.get("id")

    # MCP Protokolü El Sıkışması
    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "colab-mcp-bridge",
                    "version": "1.0.0"
                }
            }
        })

    # Spark'ın araçları listeleme isteği
    elif method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOLS_DEFINITION
            }
        })

    # Spark'ın aracı çalıştırma isteği
    elif method == "tools/call":
        params = data.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name == "whisper_transcribe":
            dosya = args.get("dosya_adi", "belirtilmedi")
            result_text = f"'{dosya}' dosyası Colab GPU kuyruğuna alındı ve işleme başlandı."
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": result_text}
                    ]
                }
            })

    # Diğer tüm bildirimler / kontroller
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {}
    })

# 4. OAuth yoklama rotaları (Spark bazen 404 görünce huysuzlaşır)
@app.get("/.well-known/oauth-protected-resource")
@app.get("/.well-known/oauth-protected-resource/sse")
async def oauth_dummy():
    return JSONResponse({"status": "unprotected"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=port)
