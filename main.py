import os
from mcp.server.fastmcp import FastMCP

port = int(os.environ.get("PORT", 10000))
mcp = FastMCP("ColabBridge", host="0.0.0.0", port=port)

@mcp.tool()
def whisper_transcribe(dosya_adi: str) -> str:
    """Google Drive uzerindeki ses dosyasini transkript eder."""
    return f"'{dosya_adi}' dosyasi icin Whisper islemi tetiklendi."

if __name__ == "__main__":
    mcp.run(transport="sse")
