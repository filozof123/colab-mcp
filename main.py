import os
import uvicorn
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from mcp.server.fastmcp import FastMCP

# DNS Rebinding korumasını bulut sunucuları için yapılandırma
try:
    from mcp.server.transport_security import TransportSecuritySettings
except ImportError:
    from mcp.server.sse import TransportSecuritySettings

port = int(os.environ.get("PORT", 10000))

# 1. FastMCP nesnesini DNS Rebinding koruması kapalı olarak başlat
mcp = FastMCP(
    "ColabBridge",
    host="0.0.0.0",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
)

@mcp.tool()
def whisper_transcribe(dosya_adi: str) -> str:
    """Google Drive uzerindeki ses dosyasini transkript eder."""
    return f"'{dosya_adi}' dosyasi icin Whisper islemi tetiklendi."

# 2. FastMCP'nin SSE uygulamasını al
app = mcp.sse_app()

# Google doğrulama kontrolleri için kök dizin rotası
async def health_check(request):
    if request.method == "HEAD":
        return Response(status_code=200)
    return JSONResponse({"status": "ok", "service": "Colab-MCP Server"})

app.routes.insert(0, Route("/", endpoint=health_check, methods=["GET", "HEAD"]))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=port)
