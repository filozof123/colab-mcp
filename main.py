import os
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from mcp.server.fastmcp import FastMCP

port = int(os.environ.get("PORT", 10000))

# MCP Nesnesi
mcp = FastMCP("ColabBridge")

@mcp.tool()
def whisper_transcribe(dosya_adi: str) -> str:
    """Google Drive uzerindeki ses dosyasini transkript eder."""
    return f"'{dosya_adi}' dosyasi icin Whisper islemi tetiklendi."

# FastMCP'nin yerleşik SSE uygulamasını al
app = mcp.sse_app()

# Google doğrulama kontrolleri için kök dizin rotaları
async def health_check(request):
    if request.method == "HEAD":
        return Response(status_code=200)
    return JSONResponse({"status": "ok", "service": "Colab-MCP Server"})

# Kök dizin rotasını en başa ekle
app.routes.insert(0, Route("/", endpoint=health_check, methods=["GET", "HEAD"]))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=port)
