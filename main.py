import os
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
from mcp.server.fastmcp import FastMCP
import uvicorn

port = int(os.environ.get("PORT", 10000))
mcp = FastMCP("ColabBridge")

@mcp.tool()
def whisper_transcribe(dosya_adi: str) -> str:
    """Google Drive uzerindeki ses dosyasini transkript eder."""
    return f"'{dosya_adi}' dosyasi icin Whisper islemi tetiklendi."

# Google / Gemini kontrol istekleri icin kok dizine 200 OK yaniti
async def health_check(request):
    return JSONResponse({"status": "ok", "service": "Colab-MCP Server"})

# FastMCP'nin SSE uygulamasini al ve kok route ekle
app = mcp._create_sse_app()
app.routes.insert(0, Route("/", endpoint=health_check, methods=["GET", "HEAD"]))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=port)
