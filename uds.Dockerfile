# Dockerfile.uds
# Dedicated Dockerfile for Unix Domain Socket (UDS) + SSE setup

# Use the official uv image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install dependencies
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-install-project

# 2. Copy source code
COPY . .

# 3. Install project
RUN uv sync

ENV PATH="/app/.venv/bin:$PATH"

# Create directories for sockets
# /var/run/redis -> for Redis socket
# /var/run/mcp   -> for MCP Server socket
RUN mkdir -p /var/run/redis /var/run/mcp

# DEFAULT COMMAND
# We set this here so you don't HAVE to type it in Docker Compose.
# It defaults to SSE mode using a socket file.
# You can override this command in docker-compose.yml if needed.
CMD ["redis-mcp-server", "--transport", "sse", "--uds", "/var/run/mcp/mcp.sock"]