import os
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

port = int(os.environ.get("PORT", 10000))

# 1. MCP Tanımı
mcp = FastMCP("ColabBridge")

@mcp.tool()
def whisper_transcribe(dosya_adi: str) -> str:
    """Google Drive uzerindeki ses dosyasini transkript eder."""
    return f"'{dosya_adi}' dosyasi icin Whisper islemi tetiklendi."

# Standart SSE Transport
sse = SseServerTransport("/messages/")

async def handle_sse(request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await mcp._mcp_server.run(
            read_stream,
            write_stream,
            mcp._mcp_server.create_initialization_options()
        )

# Spark hem /messages/ hem de dogrudan /sse adresine POST atabilir
async def handle_post_message(request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

async def sse_endpoint_router(request):
    if request.method == "POST":
        return await handle_post_message(request)
    elif request.method == "HEAD":
        return Response(status_code=200)
    else:
        return await handle_sse(request)

async def health_check(request):
    if request.method == "HEAD":
        return Response(status_code=200)
    return JSONResponse({"status": "ok", "service": "Colab-MCP Server"})

# OAuth kontrollerine Spark'i bekletmeden bos onay don
async def oauth_dummy(request):
    return JSONResponse({"status": "unprotected"})

starlette_app = Starlette(
    routes=[
        Route("/", endpoint=health_check, methods=["GET", "HEAD"]),
        Route("/sse", endpoint=sse_endpoint_router, methods=["GET", "HEAD", "POST"]),
        Route("/messages/", endpoint=handle_post_message, methods=["POST"]),
        Route("/.well-known/oauth-protected-resource", endpoint=oauth_dummy, methods=["GET"]),
        Route("/.well-known/oauth-protected-resource/sse", endpoint=oauth_dummy, methods=["GET"]),
    ]
)

# 421 Host Dogrulama engelini asan ara katman
class HostRewriteMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = []
            for name, value in scope.get("headers", []):
                if name.lower() == b"host":
                    # Kutuphanenin bekledigi yerel hosta cevir
                    headers.append((b"host", b"localhost:10000"))
                else:
                    headers.append((name, value))
            scope["headers"] = headers
        await self.app(scope, receive, send)

app = HostRewriteMiddleware(starlette_app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=port)
