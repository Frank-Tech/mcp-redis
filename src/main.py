import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

import click
import uvicorn
from fastmcp.server.http import create_sse_app
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount
from starlette.types import Scope, Receive, Send

from src.common.config import (
    parse_redis_uri,
    set_redis_config_from_cli,
    set_entraid_config_from_cli,
)
from src.common.logging_utils import configure_logging
from src.common.server import mcp

logger = logging.getLogger(__name__)


def apply_config_from_env():
    """
    Reads configuration from Environment Variables (set by the main process)
    and applies them to the global application state inside the worker.
    """
    # 1. Reconstruct Redis Configuration
    redis_config = {}

    # Check for direct connection params
    if os.getenv("REDIS_HOST"):
        redis_config["host"] = os.getenv("REDIS_HOST")
    if os.getenv("REDIS_PORT"):
        redis_config["port"] = int(os.getenv("REDIS_PORT"))
    if os.getenv("REDIS_DB"):
        redis_config["db"] = int(os.getenv("REDIS_DB"))
    if os.getenv("REDIS_USERNAME"):
        redis_config["username"] = os.getenv("REDIS_USERNAME")
    if os.getenv("REDIS_PWD"):
        redis_config["password"] = os.getenv("REDIS_PWD")
    if os.getenv("REDIS_MAX_CONNECTIONS"):
        redis_config["max_connections"] = int(os.getenv("REDIS_MAX_CONNECTIONS"))
    if os.getenv("REDIS_UNIX_SOCKET_PATH"):
        redis_config["unix_socket_path"] = os.getenv("REDIS_UNIX_SOCKET_PATH")

    # Boolean flags
    if os.getenv("REDIS_SSL") == "true":
        redis_config["ssl"] = True
    if os.getenv("REDIS_CLUSTER_MODE") == "true":
        redis_config["cluster_mode"] = True

    # SSL Cert details
    if os.getenv("REDIS_SSL_CA_PATH"):
        redis_config["ssl_ca_path"] = os.getenv("REDIS_SSL_CA_PATH")
    if os.getenv("REDIS_SSL_KEYFILE"):
        redis_config["ssl_keyfile"] = os.getenv("REDIS_SSL_KEYFILE")
    if os.getenv("REDIS_SSL_CERTFILE"):
        redis_config["ssl_certfile"] = os.getenv("REDIS_SSL_CERTFILE")
    if os.getenv("REDIS_SSL_CERT_REQS"):
        redis_config["ssl_cert_reqs"] = os.getenv("REDIS_SSL_CERT_REQS")
    if os.getenv("REDIS_SSL_CA_CERTS"):
        redis_config["ssl_ca_certs"] = os.getenv("REDIS_SSL_CA_CERTS")

    # Apply Redis Config
    if redis_config:
        set_redis_config_from_cli(redis_config)

    # 2. Reconstruct Entra ID Configuration
    entraid_config = {}
    if os.getenv("REDIS_ENTRAID_AUTH_FLOW"):
        entraid_config["auth_flow"] = os.getenv("REDIS_ENTRAID_AUTH_FLOW")
    if os.getenv("REDIS_ENTRAID_CLIENT_ID"):
        entraid_config["client_id"] = os.getenv("REDIS_ENTRAID_CLIENT_ID")
    if os.getenv("REDIS_ENTRAID_USER_ASSIGNED_CLIENT_ID"):
        entraid_config["user_assigned_identity_client_id"] = os.getenv(
            "REDIS_ENTRAID_USER_ASSIGNED_CLIENT_ID"
        )
    if os.getenv("REDIS_ENTRAID_CLIENT_SECRET"):
        entraid_config["client_secret"] = os.getenv("REDIS_ENTRAID_CLIENT_SECRET")
    if os.getenv("REDIS_ENTRAID_TENANT_ID"):
        entraid_config["tenant_id"] = os.getenv("REDIS_ENTRAID_TENANT_ID")
    if os.getenv("REDIS_ENTRAID_IDENTITY_TYPE"):
        entraid_config["identity_type"] = os.getenv("REDIS_ENTRAID_IDENTITY_TYPE")
    if os.getenv("REDIS_ENTRAID_SCOPES"):
        entraid_config["scopes"] = os.getenv("REDIS_ENTRAID_SCOPES")
    if os.getenv("REDIS_ENTRAID_RESOURCE"):
        entraid_config["resource"] = os.getenv("REDIS_ENTRAID_RESOURCE")
    if os.getenv("REDIS_ENTRAID_TOKEN_EXPIRATION_REFRESH_RATIO"):
        entraid_config["token_expiration_refresh_ratio"] = float(
            os.getenv("REDIS_ENTRAID_TOKEN_EXPIRATION_REFRESH_RATIO")
        )
    if os.getenv("REDIS_ENTRAID_RETRY_MAX_ATTEMPTS"):
        entraid_config["retry_max_attempts"] = int(
            os.getenv("REDIS_ENTRAID_RETRY_MAX_ATTEMPTS")
        )
    if os.getenv("REDIS_ENTRAID_RETRY_DELAY_MS"):
        entraid_config["retry_delay_ms"] = int(
            os.getenv("REDIS_ENTRAID_RETRY_DELAY_MS")
        )

    # Apply Entra ID Config
    if entraid_config:
        set_entraid_config_from_cli(entraid_config)


def create_app():
    """
    ASGI App Factory used by Uvicorn workers.
    """
    transport = os.getenv("TRANSPORT", "http")
    app_state = {}

    @asynccontextmanager
    async def worker_lifespan(app):
        # 1. Initialize Logging for this worker
        configure_logging()

        # 2. Apply Configuration (read from Env Vars passed by CLI)
        try:
            apply_config_from_env()
            logger.info(f"Worker initialized with transport: {transport}")
        except Exception as e:
            logger.exception("Failed to apply configuration in worker")
            raise e

        # 3. Initialize the Inner FastMCP App
        # Note: 'mcp' is imported from src.common.server
        try:
            if transport == "sse":
                logger.info("Initializing SSE App")
                inner_app = create_sse_app(
                    mcp, sse_path="/sse", message_path="/messages"
                )
            else:
                logger.info("Initializing HTTP App")
                inner_app = mcp.http_app()

            app_state["app"] = inner_app

            # 4. Chain the Inner App's Lifespan
            # This ensures FastMCP background tasks (ping/pong, sessions) are started.
            if hasattr(inner_app, "router") and hasattr(
                inner_app.router, "lifespan_context"
            ):
                async with inner_app.router.lifespan_context(inner_app):
                    yield
            else:
                yield

        except Exception as e:
            logger.exception("Failed to initialize worker application")
            raise e

    async def dispatch(scope: Scope, receive: Receive, send: Send):
        """Forward requests to the inner app."""
        if scope["type"] == "lifespan":
            return

        if "app" in app_state:
            try:
                await app_state["app"](scope, receive, send)
            except Exception as e:
                logger.exception("Error processing request in redis mcp app")
                try:
                    response = JSONResponse(
                        {"error": "Internal Server Error", "detail": str(e)},
                        status_code=500,
                    )
                    await response(scope, receive, send)
                except RuntimeError:
                    pass
        else:
            response = JSONResponse(
                {"error": "Service Unavailable", "detail": "Initializing..."},
                status_code=503,
            )
            await response(scope, receive, send)

    return Starlette(lifespan=worker_lifespan, routes=[Mount("/", app=dispatch)])


async def _run_stdio_mode():
    """Helper to run STDIO mode within an async loop."""
    configure_logging()
    # Note: In STDIO mode, config is already set in the main process before calling this,
    # but strictly speaking, apply_config_from_env() would work if env vars are set.
    # However, since stdio is single process, we can rely on global state set in run_redis_server.
    await mcp.run_async(transport="stdio")


def run_redis_server(
    transport: str,
    mcp_host: str,
    mcp_port: int,
    workers: int,
    uds: str = None,
    uvicorn_kwargs: Dict[str, Any] = None,
    **redis_kwargs,  # All the redis config options
) -> int:
    if uvicorn_kwargs is None:
        uvicorn_kwargs = {}

    # --- 1. Prepare Configuration (Env Vars) ---

    # Basic Redis
    if redis_kwargs.get("host"):
        os.environ["REDIS_HOST"] = redis_kwargs["host"]
    if redis_kwargs.get("port"):
        os.environ["REDIS_PORT"] = str(redis_kwargs["port"])
    if redis_kwargs.get("password"):
        os.environ["REDIS_PWD"] = redis_kwargs["password"]
    if redis_kwargs.get("max_connections"):
        os.environ["REDIS_MAX_CONNECTIONS"] = str(redis_kwargs["max_connections"])
    if redis_kwargs.get("db"):
        os.environ["REDIS_DB"] = str(redis_kwargs["db"])
    if redis_kwargs.get("username"):
        os.environ["REDIS_USERNAME"] = redis_kwargs["username"]
    if redis_kwargs.get("redis_unix_socket_path"):
        os.environ["REDIS_UNIX_SOCKET_PATH"] = redis_kwargs["redis_unix_socket_path"]

    # SSL / Cluster
    if redis_kwargs.get("ssl"):
        os.environ["REDIS_SSL"] = "true"
    if redis_kwargs.get("cluster_mode"):
        os.environ["REDIS_CLUSTER_MODE"] = "true"
    if redis_kwargs.get("ssl_ca_path"):
        os.environ["REDIS_SSL_CA_PATH"] = redis_kwargs["ssl_ca_path"]
    if redis_kwargs.get("ssl_keyfile"):
        os.environ["REDIS_SSL_KEYFILE"] = redis_kwargs["ssl_keyfile"]
    if redis_kwargs.get("ssl_certfile"):
        os.environ["REDIS_SSL_CERTFILE"] = redis_kwargs["ssl_certfile"]
    if redis_kwargs.get("ssl_cert_reqs"):
        os.environ["REDIS_SSL_CERT_REQS"] = redis_kwargs["ssl_cert_reqs"]
    if redis_kwargs.get("ssl_ca_certs"):
        os.environ["REDIS_SSL_CA_CERTS"] = redis_kwargs["ssl_ca_certs"]

    # Entra ID
    if redis_kwargs.get("entraid_auth_flow"):
        os.environ["REDIS_ENTRAID_AUTH_FLOW"] = redis_kwargs["entraid_auth_flow"]
    if redis_kwargs.get("entraid_client_id"):
        os.environ["REDIS_ENTRAID_CLIENT_ID"] = redis_kwargs["entraid_client_id"]
        if (
            redis_kwargs.get("entraid_auth_flow") == "managed_identity"
            and redis_kwargs.get("entraid_identity_type") == "user_assigned"
        ):
            os.environ["REDIS_ENTRAID_USER_ASSIGNED_CLIENT_ID"] = redis_kwargs[
                "entraid_client_id"
            ]

    if redis_kwargs.get("entraid_client_secret"):
        os.environ["REDIS_ENTRAID_CLIENT_SECRET"] = redis_kwargs[
            "entraid_client_secret"
        ]
    if redis_kwargs.get("entraid_tenant_id"):
        os.environ["REDIS_ENTRAID_TENANT_ID"] = redis_kwargs["entraid_tenant_id"]
    if redis_kwargs.get("entraid_identity_type"):
        os.environ["REDIS_ENTRAID_IDENTITY_TYPE"] = redis_kwargs[
            "entraid_identity_type"
        ]
    if redis_kwargs.get("entraid_scopes"):
        os.environ["REDIS_ENTRAID_SCOPES"] = redis_kwargs["entraid_scopes"]
    if redis_kwargs.get("entraid_resource"):
        os.environ["REDIS_ENTRAID_RESOURCE"] = redis_kwargs["entraid_resource"]
    if redis_kwargs.get("entraid_token_refresh_ratio"):
        os.environ["REDIS_ENTRAID_TOKEN_EXPIRATION_REFRESH_RATIO"] = str(
            redis_kwargs["entraid_token_refresh_ratio"]
        )
    if redis_kwargs.get("entraid_retry_max_attempts"):
        os.environ["REDIS_ENTRAID_RETRY_MAX_ATTEMPTS"] = str(
            redis_kwargs["entraid_retry_max_attempts"]
        )
    if redis_kwargs.get("entraid_retry_delay_ms"):
        os.environ["REDIS_ENTRAID_RETRY_DELAY_MS"] = str(
            redis_kwargs["entraid_retry_delay_ms"]
        )

    os.environ["TRANSPORT"] = transport

    # --- 2. Validation & Mode Selection ---

    if uds and sys.platform == "win32":
        raise click.BadParameter("Unix Domain Sockets are not supported on Windows.")

    if transport == "stdio":
        if workers > 1:
            raise click.BadParameter("Cannot use workers with stdio transport")

        # Apply config locally for the single process
        apply_config_from_env()
        try:
            asyncio.run(_run_stdio_mode())
        except KeyboardInterrupt:
            pass
        return 0

    # --- 3. Run Uvicorn (HTTP/SSE) ---
    config_kwargs = {
        "ws": "wsproto",
        "loop": "auto",
        "http": "auto",
        "timeout_keep_alive": 30,
    }
    config_kwargs.update(uvicorn_kwargs)

    if uds:
        logger.info(f"Binding to Unix Domain Socket: {uds}")
        config_kwargs["uds"] = uds
    else:
        logger.info(f"Binding to TCP: {mcp_host}:{mcp_port}")
        config_kwargs["host"] = mcp_host
        config_kwargs["port"] = mcp_port

    uvicorn.run(
        "src.main:create_app", workers=workers or 1, factory=True, **config_kwargs
    )
    return 0


@click.command()
@click.option(
    "--transport", default="stdio", help="Transport mechanism (stdio, http, sse)."
)
@click.option("--mcp-host", default="127.0.0.1", help="MCP host (for Uvicorn).")
@click.option("--mcp-port", default=8000, type=int, help="MCP port (for Uvicorn).")
@click.option("--uds", default=None, help="Unix Domain Socket path.")
@click.option("--url", help="Redis connection URI.")
@click.option("--host", default="127.0.0.1", help="Redis host")
@click.option("--port", default=6379, type=int, help="Redis port")
@click.option(
    "--redis-unix-socket-path", default=None, help="Redis Unix Domain Socket path"
)
@click.option("--db", default=0, type=int, help="Redis database number")
@click.option("--username", help="Redis username")
@click.option("--password", help="Redis password")
@click.option("--ssl", is_flag=True, help="Use SSL connection")
@click.option("--ssl-ca-path", help="Path to CA certificate file")
@click.option("--ssl-keyfile", help="Path to SSL key file")
@click.option("--ssl-certfile", help="Path to SSL certificate file")
@click.option(
    "--ssl-cert-reqs", default="required", help="SSL certificate requirements"
)
@click.option("--ssl-ca-certs", help="Path to CA certificates file")
@click.option("--cluster-mode", is_flag=True, help="Enable Redis cluster mode")
@click.option(
    "--max-connections",
    default=None,
    type=int,
    help="Maximum number of Redis connections",
)
@click.option("--workers", default=1, type=int, help="Number of worker processes")
# Entra ID Options
@click.option(
    "--entraid-auth-flow",
    type=click.Choice(["service_principal", "managed_identity", "default_credential"]),
)
@click.option("--entraid-client-id", help="Entra ID client ID")
@click.option("--entraid-client-secret", help="Entra ID client secret")
@click.option("--entraid-tenant-id", help="Entra ID tenant ID")
@click.option(
    "--entraid-identity-type",
    type=click.Choice(["system_assigned", "user_assigned"]),
    default="system_assigned",
)
@click.option("--entraid-scopes", default="https://redis.azure.com/.default")
@click.option("--entraid-resource", default="https://redis.azure.com/")
@click.option("--entraid-token-refresh-ratio", type=float, default=0.9)
@click.option("--entraid-retry-max-attempts", type=int, default=3)
@click.option("--entraid-retry-delay-ms", type=int, default=100)
def cli(
    transport,
    mcp_host,
    mcp_port,
    uds,
    url,
    host,
    port,
    redis_unix_socket_path,
    db,
    username,
    password,
    ssl,
    ssl_ca_path,
    ssl_keyfile,
    ssl_certfile,
    ssl_cert_reqs,
    ssl_ca_certs,
    cluster_mode,
    max_connections,
    workers,
    entraid_auth_flow,
    entraid_client_id,
    entraid_client_secret,
    entraid_tenant_id,
    entraid_identity_type,
    entraid_scopes,
    entraid_resource,
    entraid_token_refresh_ratio,
    entraid_retry_max_attempts,
    entraid_retry_delay_ms,
):
    """Redis MCP Server - Model Context Protocol server for Redis."""

    # 1. Handle Redis URI parsing explicitly before anything else
    redis_params = {
        "host": host,
        "port": port,
        "db": db,
        "username": username,
        "password": password,
        "redis_unix_socket_path": redis_unix_socket_path,
        "ssl": ssl,
        "cluster_mode": cluster_mode,
        "max_connections": max_connections,
        "ssl_ca_path": ssl_ca_path,
        "ssl_keyfile": ssl_keyfile,
        "ssl_certfile": ssl_certfile,
        "ssl_cert_reqs": ssl_cert_reqs,
        "ssl_ca_certs": ssl_ca_certs,
        "entraid_auth_flow": entraid_auth_flow,
        "entraid_client_id": entraid_client_id,
        "entraid_client_secret": entraid_client_secret,
        "entraid_tenant_id": entraid_tenant_id,
        "entraid_identity_type": entraid_identity_type,
        "entraid_scopes": entraid_scopes,
        "entraid_resource": entraid_resource,
        "entraid_token_refresh_ratio": entraid_token_refresh_ratio,
        "entraid_retry_max_attempts": entraid_retry_max_attempts,
        "entraid_retry_delay_ms": entraid_retry_delay_ms,
    }

    if url and url.strip() and url.strip() != "${REDIS_URL}":
        try:
            uri_config = parse_redis_uri(url)
            # Merge URI config into redis_params, overriding defaults but not explicit args if set?
            # Usually URI overrides defaults. We simply map valid keys.
            for key, value in uri_config.items():
                if value is not None:
                    # Map uri_config keys to our expected keys if they differ, or rely on consistency
                    redis_params[key] = value
        except ValueError as e:
            raise click.BadParameter(f"Error parsing Redis URI: {e}")

    try:
        run_redis_server(
            transport=transport,
            mcp_host=mcp_host,
            mcp_port=mcp_port,
            workers=workers,
            uds=uds,
            **redis_params,
        )
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt")
        sys.exit(130)
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    cli()
