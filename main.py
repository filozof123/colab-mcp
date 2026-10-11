import os
import uvicorn
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from mcp.server.fastmcp import FastMCP

port = int(os.environ.get("PORT", 10000))

# 1. MCP Tanımı
mcp = FastMCP("ColabBridge")

@mcp.tool()
def whisper_transcribe(dosya_adi: str) -> str:
    """Google Drive uzerindeki ses dosyasini transkript eder."""
    return f"'{dosya_adi}' dosyasi icin Whisper islemi tetiklendi."

# 2. FastMCP'nin kendi tam donanimli SSE uygulamasini al
# Bu uygulama /sse ve /messages rotalarini protokol kurallarina tam uygun sekilde yonetir
core_app = mcp.sse_app()

# Google'in kok dizin (/) saglik kontrolleri icin 200 yaniti ekle
async def health_check(request):
    if request.method == "HEAD":
        return Response(status_code=200)
    return JSONResponse({"status": "ok", "service": "Colab-MCP Server"})

core_app.routes.insert(0, Route("/", endpoint=health_check, methods=["GET", "HEAD"]))

# 3. Host Validation (421 Misdirected Request) hatasini onleyen ara katman
class HostRewriteMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = []
            for name, value in scope.get("headers", []):
                if name.lower() == b"host":
                    headers.append((b"host", b"localhost"))
                else:
                    headers.append((name, value))
            scope["headers"] = headers
        await self.app(scope, receive, send)

app = HostRewriteMiddleware(core_app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=port)
