from typing import List, Any, Union

from redis.exceptions import RedisError, NoScriptError

from src.common.connection import RedisConnectionManager
from src.common.server import mcp


def _recursive_decode(data: Any) -> Any:
    """Helper to recursively decode bytes to strings in Lua responses."""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    if isinstance(data, list):
        return [_recursive_decode(item) for item in data]
    if isinstance(data, dict):
        return {_recursive_decode(k): _recursive_decode(v) for k, v in data.items()}
    return data


@mcp.tool()
async def eval_script(
    script: str, keys: List[str], args: List[str]
) -> Union[str, int, List[Any], None]:
    """Execute a Lua script on the Redis server.

    Args:
        script: The Lua script source code.
        keys: A list of keys accessed by the script (KEYS[1], KEYS[2], ...).
        args: A list of arguments passed to the script (ARGV[1], ARGV[2], ...).

    Returns:
        The result of the Lua script (decoded to strings/lists/dicts).
    """
    try:
        r = RedisConnectionManager.get_connection()
        # redis-py eval signature: eval(script, numkeys, *keys_and_args)
        # We generally use: await r.eval(script, len(keys), *keys, *args)

        result = await r.eval(script, len(keys), *keys, *args)
        return _recursive_decode(result)

    except RedisError as e:
        return f"Error executing Lua script: {str(e)}"


@mcp.tool()
async def script_load(script: str) -> str:
    """Load a Lua script into the Redis script cache.

    Args:
        script: The Lua script source code.

    Returns:
        The SHA1 digest of the stored script, or an error message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        sha = await r.script_load(script)
        return sha
    except RedisError as e:
        return f"Error loading script: {str(e)}"


@mcp.tool()
async def evalsha_script(
    sha: str, keys: List[str], args: List[str]
) -> Union[str, int, List[Any], None]:
    """Execute a Lua script by its SHA1 digest.

    Args:
        sha: The SHA1 digest of the script (obtained via script_load).
        keys: A list of keys accessed by the script.
        args: A list of arguments passed to the script.

    Returns:
        The result of the Lua script.
    """
    try:
        r = RedisConnectionManager.get_connection()
        try:
            result = await r.evalsha(sha, len(keys), *keys, *args)
            return _recursive_decode(result)
        except NoScriptError:
            return "Error: NOSCRIPT No matching script. Please load it first using script_load."

    except RedisError as e:
        return f"Error executing cached script (SHA: {sha}): {str(e)}"


@mcp.tool()
async def script_exists(sha: str) -> bool:
    """Check if a script exists in the script cache.

    Args:
        sha: The SHA1 digest to check.

    Returns:
        True if exists, False otherwise.
    """
    try:
        r = RedisConnectionManager.get_connection()
        # script_exists takes a *args list of shas, returns a list of bools
        result = await r.script_exists(sha)
        return result[0] if result else False
    except RedisError as e:
        return f"Error checking script existence: {str(e)}"


@mcp.tool()
async def script_flush() -> str:
    """Flush the Redis script cache.

    Returns:
        Success message.
    """
    try:
        r = RedisConnectionManager.get_connection()
        await r.script_flush()
        return "Script cache flushed successfully."
    except RedisError as e:
        return f"Error flushing script cache: {str(e)}"
