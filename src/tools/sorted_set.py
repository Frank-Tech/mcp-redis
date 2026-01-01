from typing import Optional

from redis.exceptions import RedisError

from src.common.connection import RedisConnectionManager
from src.common.server import mcp


@mcp.tool()
async def zadd(
    key: str, score: float, member: str, expiration: Optional[int] = None
) -> str:
    """Add a member to a Redis sorted set with an optional expiration time.

    Args:
        key (str): The sorted set key.
        score (float): The score of the member.
        member (str): The member to add.
        expiration (int, optional): Expiration time in seconds.

    Returns:
        str: Number of elements added or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        result = await r.zadd(key, {member: score})
        if expiration:
            await r.expire(key, expiration)
        return str(result)
    except RedisError as e:
        return f"Error adding to sorted set {key}: {str(e)}"


@mcp.tool()
async def zrange(key: str, start: int, end: int, with_scores: bool = False) -> str:
    """Retrieve a range of members from a Redis sorted set.

    Args:
        key (str): The sorted set key.
        start (int): The starting index.
        end (int): The ending index.
        with_scores (bool, optional): Whether to include scores in the result.

    Returns:
        str: The sorted set members in the given range or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        members = await r.zrange(key, start, end, withscores=with_scores)
        return str(members)
    except RedisError as e:
        return f"Error retrieving sorted set {key}: {str(e)}"


@mcp.tool()
async def zrem(key: str, member: str) -> str:
    """Remove a member from a Redis sorted set.

    Args:
        key (str): The sorted set key.
        member (str): The member to remove.

    Returns:
        str: Number of elements removed or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        result = await r.zrem(key, member)
        return str(result)
    except RedisError as e:
        return f"Error removing from sorted set {key}: {str(e)}"


@mcp.tool()
async def zcard(key: str) -> str:
    """Retrieve the cardinality of a Redis sorted set.

    Args:
        key (str): The sorted set key.

    Returns:
        str: The number of members in the sorted set or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        count = await r.zcard(key)
        return str(count)
    except RedisError as e:
        return f"Error retrieving cardinality of sorted set {key}: {str(e)}"
