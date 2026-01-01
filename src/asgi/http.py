from src.common.server import mcp

# Configure the path as done in the original main.py logic
mcp.settings.streamable_http_path = "/mcp"

# Expose the ASGI app for Uvicorn workers
app = mcp.streamable_http_app()
