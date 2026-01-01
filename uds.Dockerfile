# Use the official uv image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install gcc and build tools required for compiling C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 1. Install dependencies
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-install-project

# 2. Copy source code
COPY . .

# 3. Install project
RUN uv sync

ENV PATH="/app/.venv/bin:$PATH"

# Create directories for sockets
RUN mkdir -p /var/run/redis /var/run/mcp

CMD ["redis-mcp-server", "--transport", "http", "--uds", "/var/run/mcp/mcp.sock"]