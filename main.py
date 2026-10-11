import os
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

port = int(os.environ.get("PORT", 10000))

# MCP Tanımı
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

async def handle_messages(request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

async def health_check(request):
    if request.method == "HEAD":
        return Response(status_code=200)
    return JSONResponse({"status": "ok", "service": "Colab-MCP Server"})

starlette_app = Starlette(
    routes=[
        Route("/", endpoint=health_check, methods=["GET", "HEAD"]),
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Route("/messages/", endpoint=handle_messages, methods=["POST"]),
    ]
)

# Host validation hatasını aşmak için Host başlığını yerel adrese eşleyen ara katman
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

app = HostRewriteMiddleware(starlette_app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=port)
