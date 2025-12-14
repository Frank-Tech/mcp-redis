from typing import Union, List, Optional

from redis.exceptions import RedisError

from src.common.connection import RedisConnectionManager
from src.common.server import mcp


@mcp.tool()
async def sadd(name: str, value: str, expire_seconds: Optional[int] = None) -> str:
    """Add a value to a Redis set with an optional expiration time.

    Args:
        name: The Redis set key.
        value: The value to add to the set.
        expire_seconds: Optional; time in seconds after which the set should expire.

    Returns:
        A success message or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        await r.sadd(name, value)

        if expire_seconds is not None:
            await r.expire(name, expire_seconds)

        return f"Value '{value}' added successfully to set '{name}'." + (
            f" Expires in {expire_seconds} seconds." if expire_seconds else ""
        )
    except RedisError as e:
        return f"Error adding value '{value}' to set '{name}': {str(e)}"


@mcp.tool()
async def srem(name: str, value: str) -> str:
    """Remove a value from a Redis set.

    Args:
        name: The Redis set key.
        value: The value to remove from the set.

    Returns:
        A success message or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        removed = await r.srem(name, value)
        return (
            f"Value '{value}' removed from set '{name}'."
            if removed
            else f"Value '{value}' not found in set '{name}'."
        )
    except RedisError as e:
        return f"Error removing value '{value}' from set '{name}': {str(e)}"


@mcp.tool()
async def smembers(name: str) -> Union[str, List[str]]:
    """Get all members of a Redis set.

    Args:
        name: The Redis set key.

    Returns:
        A list of values in the set or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        members = await r.smembers(name)
        return list(members) if members else f"Set '{name}' is empty or does not exist."
    except RedisError as e:
        return f"Error retrieving members of set '{name}': {str(e)}"


@mcp.tool()
async def scard(name: str) -> Union[str, int]:
    """Get the number of members in a set (cardinality).

    Args:
        name: The Redis set key.

    Returns:
        The count of members in the set, or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        count = await r.scard(name)
        return count
    except RedisError as e:
        return f"Error retrieving cardinality for set '{name}': {str(e)}"


@mcp.tool()
async def sismember(name: str, value: str) -> Union[str, bool]:
    """Check if a value is a member of the set.

    Args:
        name: The Redis set key.
        value: The value to check.

    Returns:
        True if the value is a member, False otherwise, or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        is_member = await r.sismember(name, value)
        return bool(is_member)
    except RedisError as e:
        return f"Error checking membership for '{value}' in set '{name}': {str(e)}"


@mcp.tool()
async def spop(name: str, count: Optional[int] = None) -> Union[str, List[str]]:
    """Remove and return one or multiple random members from a set.

    Args:
        name: The Redis set key.
        count: Optional; number of members to pop. If None, pops a single member.

    Returns:
        The popped member(s) or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        # count=None returns a single string/bytes, count=int returns a list
        popped = await r.spop(name, count)

        if popped is None:
            return f"Set '{name}' is empty or does not exist."

        # If count was provided, popped is a list, otherwise it's a single value
        return list(popped) if isinstance(popped, list) else popped
    except RedisError as e:
        return f"Error popping member(s) from set '{name}': {str(e)}"


@mcp.tool()
async def srandmember(name: str, count: Optional[int] = None) -> Union[str, List[str]]:
    """Get one or multiple random members from a set without removing them.

    Args:
        name: The Redis set key.
        count: Optional; number of members to retrieve.
               If positive, returns distinct elements.
               If negative, allows repeating elements.

    Returns:
        The random member(s) or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        members = await r.srandmember(name, count)

        if members is None:
            return f"Set '{name}' is empty or does not exist."

        return list(members) if isinstance(members, list) else members
    except RedisError as e:
        return f"Error retrieving random member(s) from set '{name}': {str(e)}"


@mcp.tool()
async def smove(source: str, destination: str, value: str) -> Union[str, bool]:
    """Move a member from the source set to the destination set.

    Args:
        source: The source set key.
        destination: The destination set key.
        value: The value to move.

    Returns:
        True if the element was moved, False if the element was not found in source, or error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        moved = await r.smove(source, destination, value)
        return bool(moved)
    except RedisError as e:
        return (
            f"Error moving value '{value}' from '{source}' to '{destination}': {str(e)}"
        )


@mcp.tool()
async def sdiff(keys: List[str]) -> Union[str, List[str]]:
    """Subtract multiple sets (set difference).

    Args:
        keys: A list of set keys. The first key is the base set,
              subsequent keys are subtracted from it.

    Returns:
        A list of members resulting from the difference, or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        if not keys:
            return "Error: At least one key must be provided for sdiff."

        difference = await r.sdiff(*keys)
        return list(difference)
    except RedisError as e:
        return f"Error calculating difference for keys {keys}: {str(e)}"


@mcp.tool()
async def sinter(keys: List[str]) -> Union[str, List[str]]:
    """Intersect multiple sets.

    Args:
        keys: A list of set keys to intersect.

    Returns:
        A list of members present in all specified sets, or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        if not keys:
            return "Error: At least one key must be provided for sinter."

        intersection = await r.sinter(*keys)
        return list(intersection)
    except RedisError as e:
        return f"Error calculating intersection for keys {keys}: {str(e)}"


@mcp.tool()
async def sunion(keys: List[str]) -> Union[str, List[str]]:
    """Add multiple sets (set union).

    Args:
        keys: A list of set keys to join.

    Returns:
        A list of unique members from all specified sets, or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        if not keys:
            return "Error: At least one key must be provided for sunion."

        union = await r.sunion(*keys)
        return list(union)
    except RedisError as e:
        return f"Error calculating union for keys {keys}: {str(e)}"
