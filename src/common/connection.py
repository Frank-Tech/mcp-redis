import logging
from typing import Optional, Type, Union

import redis.asyncio as redis
from redis import exceptions as redis_exceptions
from redis.asyncio import Redis
from redis.asyncio.cluster import RedisCluster

from src.common.config import REDIS_CFG, is_entraid_auth_enabled
from src.common.entraid_auth import (
    create_credential_provider,
    EntraIDAuthenticationError,
)
from src.version import __version__

_logger = logging.getLogger(__name__)


class RedisConnectionManager:
    _instance: Optional[Redis] = None

    @classmethod
    def get_connection(cls, decode_responses=True) -> Redis:
        if cls._instance is None:
            try:
                # Create Entra ID credential provider if configured
                credential_provider = None
                if is_entraid_auth_enabled():
                    try:
                        credential_provider = create_credential_provider()
                    except EntraIDAuthenticationError as e:
                        _logger.error(
                            "Failed to create Entra ID credential provider: %s", e
                        )
                        raise

                # Base parameters common to both modes
                base_params = {
                    "host": REDIS_CFG["host"],
                    "port": REDIS_CFG["port"],
                    "unix_socket_path": REDIS_CFG.get("unix_socket_path"),
                    "username": REDIS_CFG["username"],
                    "password": REDIS_CFG["password"],
                    "ssl": REDIS_CFG["ssl"],
                    "ssl_ca_path": REDIS_CFG["ssl_ca_path"],
                    "ssl_keyfile": REDIS_CFG["ssl_keyfile"],
                    "ssl_certfile": REDIS_CFG["ssl_certfile"],
                    "ssl_cert_reqs": REDIS_CFG["ssl_cert_reqs"],
                    "ssl_ca_certs": REDIS_CFG["ssl_ca_certs"],
                    "decode_responses": decode_responses,
                    "lib_name": f"redis-py-async(mcp-server_v{__version__})",
                }

                if REDIS_CFG["cluster_mode"]:
                    redis_class: Type[Union[Redis, RedisCluster]] = RedisCluster
                    connection_params = base_params.copy()
                    connection_params["max_connections_per_node"] = 10
                else:
                    redis_class: Type[Union[Redis, RedisCluster]] = redis.Redis
                    connection_params = base_params.copy()
                    connection_params["db"] = REDIS_CFG["db"]
                    connection_params["max_connections"] = 10

                # Add credential provider if available
                if credential_provider:
                    connection_params["credential_provider"] = credential_provider

                # CRITICAL FIX for AsyncIO:
                # The async client crashes if you pass None for keys it doesn't recognize (like ssl_ca_path).
                # We must filter out None values so we only pass arguments that are actually set.
                filtered_params = {
                    k: v for k, v in connection_params.items() if v is not None
                }

                cls._instance = redis_class(**filtered_params)

            except redis_exceptions.ConnectionError:
                _logger.error("Failed to connect to Redis server")
                raise
            except redis_exceptions.AuthenticationError:
                _logger.error("Authentication failed")
                raise
            except redis_exceptions.TimeoutError:
                _logger.error("Connection timed out")
                raise
            except redis_exceptions.ResponseError as e:
                _logger.error("Response error: %s", e)
                raise
            except redis_exceptions.RedisError as e:
                _logger.error("Redis error: %s", e)
                raise
            except redis_exceptions.ClusterError as e:
                _logger.error("Redis Cluster error: %s", e)
                raise
            except TypeError as e:
                _logger.error("Configuration error (TypeError): %s", e)
                raise
            except Exception as e:
                _logger.error("Unexpected error: %s", e)
                raise

        return cls._instance
