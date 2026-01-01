FROM python:3.14-slim

LABEL io.modelcontextprotocol.server.name="io.github.redis/mcp-redis"

# Install gcc and build tools required for compiling C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade uv

WORKDIR /app
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

CMD ["uv", "run", "python", "src/main.py"]
