import json
from typing import Dict, Any, Optional

from redis.exceptions import RedisError

from src.common.connection import RedisConnectionManager
from src.common.server import mcp


@mcp.tool()
async def xadd(
    key: str,
    fields: Dict[str, Any],
    maxlen: Optional[int] = None,
    approximate: bool = True,
    expiration: Optional[int] = None,
) -> str:
    """Add an entry to a Redis stream. Automatically serializes dict/list values to JSON.

    Args:
        key (str): The stream key.
        fields (dict): The fields. Values can be strings, numbers, or dicts (will be stringified).
        maxlen (int, optional): Maximum stream length.
        approximate (bool, optional): If True, uses '~' for efficient trimming. Defaults to True.
        expiration (int, optional): Expiration time in seconds.

    Returns:
        str: The ID of the added entry or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()

        safe_fields = {}
        for k, v in fields.items():
            if isinstance(v, (dict, list)):
                safe_fields[k] = json.dumps(v)
            else:
                safe_fields[k] = v

        entry_id = await r.xadd(
            key,
            safe_fields,
            maxlen=maxlen,
            approximate=approximate,
        )

        if expiration:
            await r.expire(key, expiration)

        return f"Successfully added entry {entry_id} to {key}"
    except RedisError as e:
        return f"Error adding to stream {key}: {str(e)}"


@mcp.tool()
async def xrange(key: str, count: int = 1) -> str:
    """Read entries from a Redis stream.

    Args:
        key (str): The stream key.
        count (int, optional): Number of entries to retrieve.

    Returns:
        str: The retrieved stream entries or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        entries = await r.xrange(key, count=count)
        return str(entries) if entries else f"Stream {key} is empty or does not exist"
    except RedisError as e:
        return f"Error reading from stream {key}: {str(e)}"


@mcp.tool()
async def xdel(key: str, entry_id: str) -> str:
    """Delete an entry from a Redis stream.

    Args:
        key (str): The stream key.
        entry_id (str): The ID of the entry to delete.

    Returns:
        str: Confirmation message or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        result = await r.xdel(key, entry_id)
        return (
            f"Successfully deleted entry {entry_id} from {key}"
            if result
            else f"Entry {entry_id} not found in {key}"
        )
    except RedisError as e:
        return f"Error deleting from stream {key}: {str(e)}"
