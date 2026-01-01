from src.common.server import mcp

# Configure the path as done in the original main.py logic
mcp.settings.sse_path = "/sse"
mcp.settings.message_path = "/message"

# Expose the ASGI app for Uvicorn workers
app = mcp.sse_app()
