"""
Unit tests for src/tools/lua.py
"""

from unittest.mock import AsyncMock

import pytest
from redis.exceptions import NoScriptError, RedisError

from src.tools.lua import (
    eval_script,
    evalsha_script,
    script_exists,
    script_flush,
    script_load,
)


@pytest.mark.asyncio
class TestLuaOperations:
    """Test cases for Redis Lua scripting operations."""

    async def test_eval_script_success(self, mock_redis_connection_manager):
        """Test successful script evaluation."""
        mock_redis = mock_redis_connection_manager
        mock_redis.eval = AsyncMock(return_value=b"result")

        keys = ["key1", "key2"]
        args = ["arg1", "arg2"]
        script = "return redis.call('get', KEYS[1])"

        result = await eval_script(script, keys, args)

        # verify (script, numkeys, *keys, *args)
        mock_redis.eval.assert_called_once_with(
            script, 2, "key1", "key2", "arg1", "arg2"
        )
        assert result == "result"

    async def test_eval_script_redis_error(self, mock_redis_connection_manager):
        """Test script evaluation with Redis error."""
        mock_redis = mock_redis_connection_manager
        mock_redis.eval = AsyncMock(side_effect=RedisError("Script execution failed"))

        result = await eval_script("return 1", [], [])

        assert "Error executing Lua script: Script execution failed" in result

    async def test_script_load_success(self, mock_redis_connection_manager):
        """Test successful script loading."""
        mock_redis = mock_redis_connection_manager
        expected_sha = "a1b2c3d4e5"
        mock_redis.script_load = AsyncMock(return_value=expected_sha)

        script = "return 1"
        result = await script_load(script)

        mock_redis.script_load.assert_called_once_with(script)
        assert result == expected_sha

    async def test_script_load_error(self, mock_redis_connection_manager):
        """Test script loading error."""
        mock_redis = mock_redis_connection_manager
        mock_redis.script_load = AsyncMock(side_effect=RedisError("Load failed"))

        result = await script_load("return 1")

        assert "Error loading script: Load failed" in result

    async def test_evalsha_script_success(self, mock_redis_connection_manager):
        """Test successful cached script evaluation."""
        mock_redis = mock_redis_connection_manager
        mock_redis.evalsha = AsyncMock(return_value=b"cached_result")

        sha = "a1b2c3"
        keys = ["k1"]
        args = ["a1"]

        result = await evalsha_script(sha, keys, args)

        mock_redis.evalsha.assert_called_once_with(sha, 1, "k1", "a1")
        assert result == "cached_result"

    async def test_evalsha_script_not_found(self, mock_redis_connection_manager):
        """Test cached script evaluation when script is missing (NOSCRIPT)."""
        mock_redis = mock_redis_connection_manager
        mock_redis.evalsha = AsyncMock(side_effect=NoScriptError("No matching script"))

        result = await evalsha_script("invalid_sha", [], [])

        assert "Error: NOSCRIPT" in result
        assert "Please load it first" in result

    async def test_evalsha_script_generic_error(self, mock_redis_connection_manager):
        """Test cached script evaluation with generic error."""
        mock_redis = mock_redis_connection_manager
        mock_redis.evalsha = AsyncMock(side_effect=RedisError("Execution error"))

        result = await evalsha_script("sha", [], [])

        assert "Error executing cached script" in result
        assert "Execution error" in result

    async def test_script_exists_true(self, mock_redis_connection_manager):
        """Test script exists check returning True."""
        mock_redis = mock_redis_connection_manager
        # redis returns a list of booleans corresponding to the SHAs passed
        mock_redis.script_exists = AsyncMock(return_value=[True])

        result = await script_exists("valid_sha")

        mock_redis.script_exists.assert_called_once_with("valid_sha")
        assert result is True

    async def test_script_exists_false(self, mock_redis_connection_manager):
        """Test script exists check returning False."""
        mock_redis = mock_redis_connection_manager
        mock_redis.script_exists = AsyncMock(return_value=[False])

        result = await script_exists("missing_sha")

        assert result is False

    async def test_script_exists_error(self, mock_redis_connection_manager):
        """Test script exists check with error."""
        mock_redis = mock_redis_connection_manager
        mock_redis.script_exists = AsyncMock(side_effect=RedisError("Check failed"))

        result = await script_exists("sha")

        assert "Error checking script existence: Check failed" in result

    async def test_script_flush_success(self, mock_redis_connection_manager):
        """Test successful script cache flush."""
        mock_redis = mock_redis_connection_manager
        mock_redis.script_flush = AsyncMock(return_value=True)

        result = await script_flush()

        mock_redis.script_flush.assert_called_once()
        assert "Script cache flushed successfully" in result

    async def test_script_flush_error(self, mock_redis_connection_manager):
        """Test script flush with error."""
        mock_redis = mock_redis_connection_manager
        mock_redis.script_flush = AsyncMock(side_effect=RedisError("Flush failed"))

        result = await script_flush()

        assert "Error flushing script cache: Flush failed" in result

    async def test_recursive_decode(self, mock_redis_connection_manager):
        """Test that the recursive decoder handles nested structures."""
        mock_redis = mock_redis_connection_manager

        # Structure: List containing bytes, int, and a nested list/dict
        complex_response = [b"string", 123, [b"nested"], {b"key": b"value"}]

        mock_redis.eval = AsyncMock(return_value=complex_response)

        result = await eval_script("return complex", [], [])

        assert result[0] == "string"
        assert result[1] == 123
        assert result[2] == ["nested"]
        assert result[3] == {"key": "value"}
