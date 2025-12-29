import json
from typing import Optional, Union

from redis.exceptions import RedisError

from src.common.connection import RedisConnectionManager
from src.common.server import mcp


@mcp.tool()
async def json_set(
    name: str,
    path: str,
    value: str,
    expire_seconds: Optional[int] = None,
) -> str:
    """Set a JSON value in Redis at a given path with an optional expiration time.

    Args:
        name: The Redis key where the JSON document is stored.
        path: The JSON path where the value should be set.
        value: The JSON value to store (as JSON string, or will be auto-converted).
        expire_seconds: Optional; time in seconds after which the key should expire.

    Returns:
        A success message or an error message.
    """
    # Try to parse the value as JSON, if it fails, treat it as a plain string
    try:
        parsed_value = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        parsed_value = value

    try:
        r = RedisConnectionManager.get_connection()
        await r.json().set(name, path, parsed_value)

        if expire_seconds is not None:
            await r.expire(name, expire_seconds)

        return f"JSON value set at path '{path}' in '{name}'." + (
            f" Expires in {expire_seconds} seconds." if expire_seconds else ""
        )
    except RedisError as e:
        return f"Error setting JSON value at path '{path}' in '{name}': {str(e)}"


@mcp.tool()
async def json_get(name: str, path: str = "$") -> str:
    """Retrieve a JSON value from Redis at a given path.

    Args:
        name: The Redis key where the JSON document is stored.
        path: The JSON path to retrieve (default: root '$').

    Returns:
        The retrieved JSON value or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        value = await r.json().get(name, path)
        if value is not None:
            # Convert the value to JSON string for consistent return type
            return json.dumps(value, ensure_ascii=False, indent=2)
        else:
            return f"No data found at path '{path}' in '{name}'."
    except RedisError as e:
        return f"Error retrieving JSON value at path '{path}' in '{name}': {str(e)}"


@mcp.tool()
async def json_del(name: str, path: str = "$") -> str:
    """Delete a JSON value from Redis at a given path.

    Args:
        name: The Redis key where the JSON document is stored.
        path: The JSON path to delete (default: root '$').

    Returns:
        A success message or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        deleted = await r.json().delete(name, path)
        return (
            f"Deleted JSON value at path '{path}' in '{name}'."
            if deleted
            else f"No JSON value found at path '{path}' in '{name}'."
        )
    except RedisError as e:
        return f"Error deleting JSON value at path '{path}' in '{name}': {str(e)}"


@mcp.tool()
async def json_numincrby(name: str, path: str, value: float) -> str:
    """Increment a number value in a JSON document by a specific amount.

    Args:
        name: The Redis key where the JSON document is stored.
        path: The JSON path to the number (e.g., '.user.credits').
        value: The amount to increment by (can be negative to decrement).

    Returns:
        The new value of the number after incrementing.
    """
    try:
        r = RedisConnectionManager.get_connection()
        new_val = await r.json().numincrby(name, path, value)

        # If the path matched multiple values, new_val might be a list
        if isinstance(new_val, list):
            return f"Updated multiple values. New values: {new_val}"

        return f"New value at '{path}' in '{name}': {new_val}"
    except RedisError as e:
        return f"Error incrementing value at '{path}' in '{name}': {str(e)}"


@mcp.tool()
async def json_arr_append(name: str, path: str, value: str) -> str:
    """Append a value to a JSON array at a specific path.

    Args:
        name: The Redis key where the JSON document is stored.
        path: The JSON path to the array (e.g., '.history').
        value: The value to append (JSON string or raw string).

    Returns:
        The new length of the array.
    """
    try:
        parsed_value = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        parsed_value = value

    try:
        r = RedisConnectionManager.get_connection()
        new_len = await r.json().arrappend(name, path, parsed_value)
        return f"Value appended. New array length at '{path}': {new_len}"
    except RedisError as e:
        return f"Error appending to array at '{path}' in '{name}': {str(e)}"


@mcp.tool()
async def json_arr_len(name: str, path: str = "$") -> str:
    """Get the length of a JSON array at a specific path.

    Args:
        name: The Redis key where the JSON document is stored.
        path: The JSON path to the array.

    Returns:
        The length of the array.
    """
    try:
        r = RedisConnectionManager.get_connection()
        length = await r.json().arrlen(name, path)
        return f"Array length at '{path}': {length}"
    except RedisError as e:
        return f"Error getting array length at '{path}' in '{name}': {str(e)}"


@mcp.tool()
async def json_arr_pop(name: str, path: str = "$", index: Optional[int] = -1) -> str:
    """Pop (remove and return) an element from a JSON array at a specific index.

    Args:
        name: The Redis key where the JSON document is stored.
        path: The JSON path to the array.
        index: The index to pop (default: -1, the last element).

    Returns:
        The popped value.
    """
    try:
        r = RedisConnectionManager.get_connection()
        popped_value = await r.json().arrpop(name, path, index)
        if popped_value is not None:
            return json.dumps(popped_value, ensure_ascii=False)
        return f"No value popped from '{path}' in '{name}' (List might be empty or path invalid)."
    except RedisError as e:
        return f"Error popping from array at '{path}' in '{name}': {str(e)}"


@mcp.tool()
async def json_obj_keys(name: str, path: str = "$") -> str:
    """Get the keys of a JSON object at a specific path.

    Args:
        name: The Redis key where the JSON document is stored.
        path: The JSON path to the object.

    Returns:
        A list of keys found in the object.
    """
    try:
        r = RedisConnectionManager.get_connection()
        keys = await r.json().objkeys(name, path)
        return f"Keys at '{path}': {keys}"
    except RedisError as e:
        return f"Error retrieving object keys at '{path}' in '{name}': {str(e)}"


@mcp.tool()
async def json_toggle(name: str, path: str) -> str:
    """Toggle a boolean value in a JSON document.

    Args:
        name: The Redis key where the JSON document is stored.
        path: The JSON path to the boolean value.

    Returns:
        The new boolean value.
    """
    try:
        r = RedisConnectionManager.get_connection()
        new_state = await r.json().toggle(name, path)
        return f"Boolean toggled. New state at '{path}': {new_state}"
    except RedisError as e:
        return f"Error toggling boolean at '{path}' in '{name}': {str(e)}"
