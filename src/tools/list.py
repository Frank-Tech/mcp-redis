import json
from typing import Union, List

from redis import RedisError

from src.common.connection import RedisConnectionManager
from src.common.helpers import serialize_value
from src.common.server import mcp
from src.common.typing import RedisSerializableValue


@mcp.tool()
async def lpush(
        name: str,
        value: Union[RedisSerializableValue, List[RedisSerializableValue]],
        expire: int = None
) -> str:
    """
    Push one or more values onto the left of a Redis list and optionally set an expiration time.
    """
    try:
        r = RedisConnectionManager.get_connection()
        if isinstance(value, list):
            serialized = [serialize_value(v) for v in value]
            r.lpush(name, *serialized)
        else:
            r.lpush(name, serialize_value(value))
        if expire:
            r.expire(name, expire)
        return f"Value(s) '{value}' pushed to the left of list '{name}'."
    except RedisError as e:
        return f"Error pushing value(s) to list '{name}': {str(e)}"

@mcp.tool()
async def rpush(
        name: str,
        value: Union[RedisSerializableValue, List[RedisSerializableValue]],
        expire: int = None) -> str:
    """
    Push one or more values onto the right of a Redis list and optionally set an expiration time.
    """
    try:
        r = RedisConnectionManager.get_connection()
        if isinstance(value, list):
            serialized = [serialize_value(v) for v in value]
            r.rpush(name, *serialized)
        else:
            r.rpush(name, serialize_value(value))
        if expire:
            r.expire(name, expire)
        return f"Value(s) '{value}' pushed to the right of list '{name}'."
    except RedisError as e:
        return f"Error pushing value(s) to list '{name}': {str(e)}"

@mcp.tool()
async def lpop(name: str) -> str:
    """Remove and return the first element from a Redis list."""
    try:
        r = RedisConnectionManager.get_connection()
        value = r.lpop(name)
        return value if value else f"List '{name}' is empty or does not exist."
    except RedisError as e:
        return f"Error popping value from list '{name}': {str(e)}"

@mcp.tool()
async def rpop(name: str) -> str:
    """Remove and return the last element from a Redis list."""
    try:
        r = RedisConnectionManager.get_connection()
        value = r.rpop(name)
        return value if value else f"List '{name}' is empty or does not exist."
    except RedisError as e:
        return f"Error popping value from list '{name}': {str(e)}"

@mcp.tool()
async def lrange(name: str, start: int, stop: int) -> list:
    """Get elements from a Redis list within a specific range.

        Returns:
        str: A JSON string containing the list of elements or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        values = r.lrange(name, start, stop)
        if not values:
            return f"List '{name}' is empty or does not exist."
        else:
            return json.dumps(values)
    except RedisError as e:
        return f"Error retrieving values from list '{name}': {str(e)}"

@mcp.tool()
async def llen(name: str) -> int:
    """Get the length of a Redis list."""
    try:
        r = RedisConnectionManager.get_connection()
        return r.llen(name)
    except RedisError as e:
        return f"Error retrieving length of list '{name}': {str(e)}"
