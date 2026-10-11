import os
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

port = int(os.environ.get("PORT", 10000))

# MCP Nesnesi
mcp = FastMCP("ColabBridge")

@mcp.tool()
def whisper_transcribe(dosya_adi: str) -> str:
    """Google Drive uzerindeki ses dosyasini transkript eder."""
    return f"'{dosya_adi}' dosyasi icin Whisper islemi tetiklendi."

# Host dogrulamasinda Render alan adina ve localhost'a izin ver
sse = SseServerTransport(
    "/messages/",
    allowed_hosts=[
        "colab-mcp-o6qd.onrender.com",
        "*.onrender.com",
        "localhost",
        "127.0.0.1",
        "0.0.0.0"
    ]
)

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

app = Starlette(
    routes=[
        Route("/", endpoint=health_check, methods=["GET", "HEAD"]),
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Route("/messages/", endpoint=handle_messages, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=port)
