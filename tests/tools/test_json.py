"""
Unit tests for src/tools/json.py
"""

import json
from unittest.mock import AsyncMock

import pytest
from redis.exceptions import RedisError

from src.tools.json import (
    json_arr_append,
    json_arr_len,
    json_arr_pop,
    json_del,
    json_get,
    json_numincrby,
    json_obj_keys,
    json_set,
    json_toggle,
)


class TestJSONOperations:
    """Test cases for Redis JSON operations."""

    @pytest.mark.asyncio
    async def test_json_set_success(
        self, mock_redis_connection_manager, sample_json_data
    ):
        """Test successful JSON set operation."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.set = AsyncMock(return_value="OK")

        result = await json_set("test_doc", "$", sample_json_data)

        mock_redis.json.return_value.set.assert_called_once_with(
            "test_doc", "$", sample_json_data
        )
        assert "JSON value set at path '$' in 'test_doc'." in result

    @pytest.mark.asyncio
    async def test_json_set_with_expiration(
        self, mock_redis_connection_manager, sample_json_data
    ):
        """Test JSON set operation with expiration."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.set = AsyncMock(return_value="OK")
        mock_redis.expire = AsyncMock(return_value=True)

        result = await json_set("test_doc", "$.name", "John Updated", 60)

        mock_redis.json.return_value.set.assert_called_once_with(
            "test_doc", "$.name", "John Updated"
        )
        mock_redis.expire.assert_called_once_with("test_doc", 60)
        assert "Expires in 60 seconds" in result

    @pytest.mark.asyncio
    async def test_json_set_nested_path(self, mock_redis_connection_manager):
        """Test JSON set operation with nested path."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.set = AsyncMock(return_value="OK")

        result = await json_set("test_doc", "$.user.profile.age", 25)

        mock_redis.json.return_value.set.assert_called_once_with(
            "test_doc", "$.user.profile.age", 25
        )
        assert "JSON value set at path '$.user.profile.age'" in result

    @pytest.mark.asyncio
    async def test_json_set_redis_error(self, mock_redis_connection_manager):
        """Test JSON set operation with Redis error."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.set = AsyncMock(
            side_effect=RedisError("JSON module not loaded")
        )

        result = await json_set("test_doc", "$", {"key": "value"})

        assert (
            "Error setting JSON value at path '$' in 'test_doc': JSON module not loaded"
            in result
        )

    @pytest.mark.asyncio
    async def test_json_get_success(
        self, mock_redis_connection_manager, sample_json_data
    ):
        """Test successful JSON get operation."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.get = AsyncMock(return_value=sample_json_data)

        result = await json_get("test_doc", "$")

        mock_redis.json.return_value.get.assert_called_once_with("test_doc", "$")
        # json_get returns a JSON string representation
        assert result == json.dumps(sample_json_data, ensure_ascii=False, indent=2)

    @pytest.mark.asyncio
    async def test_json_get_specific_field(self, mock_redis_connection_manager):
        """Test JSON get operation for specific field."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.get = AsyncMock(return_value=["John Doe"])

        result = await json_get("test_doc", "$.name")

        mock_redis.json.return_value.get.assert_called_once_with("test_doc", "$.name")
        # json_get returns a JSON string representation
        assert result == json.dumps(["John Doe"], ensure_ascii=False, indent=2)

    @pytest.mark.asyncio
    async def test_json_get_default_path(
        self, mock_redis_connection_manager, sample_json_data
    ):
        """Test JSON get operation with default path."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.get = AsyncMock(return_value=sample_json_data)

        result = await json_get("test_doc")

        mock_redis.json.return_value.get.assert_called_once_with("test_doc", "$")
        # json_get returns a JSON string representation
        assert result == json.dumps(sample_json_data, ensure_ascii=False, indent=2)

    @pytest.mark.asyncio
    async def test_json_get_not_found(self, mock_redis_connection_manager):
        """Test JSON get operation when document doesn't exist."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.get = AsyncMock(return_value=None)

        result = await json_get("nonexistent_doc", "$")

        assert "No data found at path '$' in 'nonexistent_doc'" in result

    @pytest.mark.asyncio
    async def test_json_get_redis_error(self, mock_redis_connection_manager):
        """Test JSON get operation with Redis error."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.get = AsyncMock(
            side_effect=RedisError("Connection failed")
        )

        result = await json_get("test_doc", "$")

        assert (
            "Error retrieving JSON value at path '$' in 'test_doc': Connection failed"
            in result
        )

    @pytest.mark.asyncio
    async def test_json_del_success(self, mock_redis_connection_manager):
        """Test successful JSON delete operation."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.delete = AsyncMock(return_value=1)

        result = await json_del("test_doc", "$.name")

        mock_redis.json.return_value.delete.assert_called_once_with(
            "test_doc", "$.name"
        )
        assert "Deleted JSON value at path '$.name' in 'test_doc'" in result

    @pytest.mark.asyncio
    async def test_json_del_default_path(self, mock_redis_connection_manager):
        """Test JSON delete operation with default path (entire document)."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.delete = AsyncMock(return_value=1)

        result = await json_del("test_doc")

        mock_redis.json.return_value.delete.assert_called_once_with("test_doc", "$")
        assert "Deleted JSON value at path '$' in 'test_doc'" in result

    @pytest.mark.asyncio
    async def test_json_del_not_found(self, mock_redis_connection_manager):
        """Test JSON delete operation when path doesn't exist."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.delete = AsyncMock(return_value=0)

        result = await json_del("test_doc", "$.nonexistent")

        assert "No JSON value found at path '$.nonexistent' in 'test_doc'" in result

    @pytest.mark.asyncio
    async def test_json_del_redis_error(self, mock_redis_connection_manager):
        """Test JSON delete operation with Redis error."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.delete = AsyncMock(
            side_effect=RedisError("Connection failed")
        )

        result = await json_del("test_doc", "$.name")

        assert (
            "Error deleting JSON value at path '$.name' in 'test_doc': Connection failed"
            in result
        )

    @pytest.mark.asyncio
    async def test_json_set_with_array(self, mock_redis_connection_manager):
        """Test JSON set operation with array value."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.set = AsyncMock(return_value="OK")

        array_data = ["item1", "item2", "item3"]
        result = await json_set("test_doc", "$.items", array_data)

        mock_redis.json.return_value.set.assert_called_once_with(
            "test_doc", "$.items", array_data
        )
        assert "JSON value set at path '$.items'" in result

    @pytest.mark.asyncio
    async def test_json_set_with_nested_object(self, mock_redis_connection_manager):
        """Test JSON set operation with nested object."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.set = AsyncMock(return_value="OK")

        nested_data = {
            "user": {
                "profile": {
                    "name": "John",
                    "settings": {"theme": "dark", "notifications": True},
                }
            }
        }
        result = await json_set("test_doc", "$", nested_data)

        mock_redis.json.return_value.set.assert_called_once_with(
            "test_doc", "$", nested_data
        )
        assert "JSON value set at path '$'" in result

    @pytest.mark.asyncio
    async def test_json_get_array_element(self, mock_redis_connection_manager):
        """Test JSON get operation for array element."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.get = AsyncMock(return_value=["first_item"])

        result = await json_get("test_doc", "$.items[0]")

        mock_redis.json.return_value.get.assert_called_once_with(
            "test_doc", "$.items[0]"
        )
        # json_get returns a JSON string representation
        assert result == json.dumps(["first_item"], ensure_ascii=False, indent=2)

    @pytest.mark.asyncio
    async def test_json_operations_with_numeric_values(
        self, mock_redis_connection_manager
    ):
        """Test JSON operations with numeric values."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.set = AsyncMock(return_value="OK")
        mock_redis.json.return_value.get = AsyncMock(return_value=[42])

        # Set numeric value
        await json_set("test_doc", "$.count", 42)
        mock_redis.json.return_value.set.assert_called_with("test_doc", "$.count", 42)

        # Get numeric value
        result = await json_get("test_doc", "$.count")
        assert result == json.dumps([42], ensure_ascii=False, indent=2)

    @pytest.mark.asyncio
    async def test_json_operations_with_boolean_values(
        self, mock_redis_connection_manager
    ):
        """Test JSON operations with boolean values."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.set = AsyncMock(return_value="OK")
        mock_redis.json.return_value.get = AsyncMock(return_value=[True])

        # Set boolean value
        await json_set("test_doc", "$.active", True)
        mock_redis.json.return_value.set.assert_called_with(
            "test_doc", "$.active", True
        )

        # Get boolean value
        result = await json_get("test_doc", "$.active")
        assert result == json.dumps([True], ensure_ascii=False, indent=2)

    @pytest.mark.asyncio
    async def test_json_set_expiration_error(self, mock_redis_connection_manager):
        """Test JSON set operation when expiration fails."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.set = AsyncMock(return_value="OK")
        mock_redis.expire = AsyncMock(side_effect=RedisError("Expire failed"))

        result = await json_set("test_doc", "$", {"key": "value"}, 60)

        assert (
            "Error setting JSON value at path '$' in 'test_doc': Expire failed"
            in result
        )

    @pytest.mark.asyncio
    async def test_json_del_multiple_matches(self, mock_redis_connection_manager):
        """Test JSON delete operation that matches multiple elements."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.delete = AsyncMock(
            return_value=3  # Multiple elements deleted
        )

        result = await json_del("test_doc", "$..name")

        mock_redis.json.return_value.delete.assert_called_once_with(
            "test_doc", "$..name"
        )
        assert "Deleted JSON value at path '$..name'" in result

    @pytest.mark.asyncio
    async def test_json_operations_with_null_values(
        self, mock_redis_connection_manager
    ):
        """Test JSON operations with null values."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.set = AsyncMock(return_value="OK")
        mock_redis.json.return_value.get = AsyncMock(return_value=[None])

        # Set null value
        await json_set("test_doc", "$.optional_field", None)
        mock_redis.json.return_value.set.assert_called_with(
            "test_doc", "$.optional_field", None
        )

        # Get null value
        result = await json_get("test_doc", "$.optional_field")
        assert result == json.dumps([None], ensure_ascii=False, indent=2)

    @pytest.mark.asyncio
    async def test_json_numincrby_success(self, mock_redis_connection_manager):
        """Test successful JSON numincrby operation."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.numincrby = AsyncMock(return_value=11)

        result = await json_numincrby("test_doc", ".count", 1)

        mock_redis.json.return_value.numincrby.assert_called_once_with(
            "test_doc", ".count", 1
        )
        assert "New value at '.count' in 'test_doc': 11" in result

    @pytest.mark.asyncio
    async def test_json_numincrby_bulk(self, mock_redis_connection_manager):
        """Test JSON numincrby returning a list of values."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.numincrby = AsyncMock(return_value=[11, 21])

        result = await json_numincrby("test_doc", "..count", 1)

        mock_redis.json.return_value.numincrby.assert_called_once_with(
            "test_doc", "..count", 1
        )
        assert "Updated multiple values. New values: [11, 21]" in result

    @pytest.mark.asyncio
    async def test_json_numincrby_error(self, mock_redis_connection_manager):
        """Test JSON numincrby with Redis error."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.numincrby = AsyncMock(
            side_effect=RedisError("Key not found")
        )

        result = await json_numincrby("test_doc", ".count", 1)
        assert (
            "Error incrementing value at '.count' in 'test_doc': Key not found"
            in result
        )

    @pytest.mark.asyncio
    async def test_json_arr_append_success_string(self, mock_redis_connection_manager):
        """Test JSON arr_append with a simple string value."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.arrappend = AsyncMock(return_value=5)

        result = await json_arr_append("test_doc", ".list", "new_item")

        mock_redis.json.return_value.arrappend.assert_called_once_with(
            "test_doc", ".list", "new_item"
        )
        assert "Value appended. New array length at '.list': 5" in result

    @pytest.mark.asyncio
    async def test_json_arr_append_success_json(self, mock_redis_connection_manager):
        """Test JSON arr_append with a JSON string value (auto-parsed)."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.arrappend = AsyncMock(return_value=6)

        json_input = '{"key": "val"}'
        result = await json_arr_append("test_doc", ".list", json_input)

        mock_redis.json.return_value.arrappend.assert_called_once_with(
            "test_doc", ".list", {"key": "val"}
        )
        assert "Value appended. New array length at '.list': 6" in result

    @pytest.mark.asyncio
    async def test_json_arr_append_error(self, mock_redis_connection_manager):
        """Test JSON arr_append with Redis error."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.arrappend = AsyncMock(
            side_effect=RedisError("Not an array")
        )

        result = await json_arr_append("test_doc", ".list", "val")
        assert (
            "Error appending to array at '.list' in 'test_doc': Not an array" in result
        )

    @pytest.mark.asyncio
    async def test_json_arr_len_success(self, mock_redis_connection_manager):
        """Test successful JSON arr_len operation."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.arrlen = AsyncMock(return_value=10)

        result = await json_arr_len("test_doc", ".list")

        mock_redis.json.return_value.arrlen.assert_called_once_with("test_doc", ".list")
        assert "Array length at '.list': 10" in result

    @pytest.mark.asyncio
    async def test_json_arr_len_error(self, mock_redis_connection_manager):
        """Test JSON arr_len with Redis error."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.arrlen = AsyncMock(
            side_effect=RedisError("Path invalid")
        )

        result = await json_arr_len("test_doc", ".list")
        assert (
            "Error getting array length at '.list' in 'test_doc': Path invalid"
            in result
        )

    @pytest.mark.asyncio
    async def test_json_arr_pop_success(self, mock_redis_connection_manager):
        """Test successful JSON arr_pop operation."""
        mock_redis = mock_redis_connection_manager
        popped_val = {"id": 1}
        mock_redis.json.return_value.arrpop = AsyncMock(return_value=popped_val)

        result = await json_arr_pop("test_doc", ".list", -1)

        mock_redis.json.return_value.arrpop.assert_called_once_with(
            "test_doc", ".list", -1
        )
        # Should return JSON string of the popped object
        assert result == json.dumps(popped_val, ensure_ascii=False)

    @pytest.mark.asyncio
    async def test_json_arr_pop_none(self, mock_redis_connection_manager):
        """Test JSON arr_pop when nothing is returned (empty list)."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.arrpop = AsyncMock(return_value=None)

        result = await json_arr_pop("test_doc", ".list")
        assert "No value popped from '.list' in 'test_doc'" in result

    @pytest.mark.asyncio
    async def test_json_arr_pop_error(self, mock_redis_connection_manager):
        """Test JSON arr_pop with Redis error."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.arrpop = AsyncMock(
            side_effect=RedisError("Failed to pop")
        )

        result = await json_arr_pop("test_doc", ".list")
        assert (
            "Error popping from array at '.list' in 'test_doc': Failed to pop" in result
        )

    @pytest.mark.asyncio
    async def test_json_obj_keys_success(self, mock_redis_connection_manager):
        """Test successful JSON obj_keys operation."""
        mock_redis = mock_redis_connection_manager
        keys = ["k1", "k2"]
        mock_redis.json.return_value.objkeys = AsyncMock(return_value=keys)

        result = await json_obj_keys("test_doc", ".obj")

        mock_redis.json.return_value.objkeys.assert_called_once_with("test_doc", ".obj")
        assert f"Keys at '.obj': {keys}" in result

    @pytest.mark.asyncio
    async def test_json_obj_keys_error(self, mock_redis_connection_manager):
        """Test JSON obj_keys with Redis error."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.objkeys = AsyncMock(
            side_effect=RedisError("Not an object")
        )

        result = await json_obj_keys("test_doc", ".obj")
        assert (
            "Error retrieving object keys at '.obj' in 'test_doc': Not an object"
            in result
        )

    @pytest.mark.asyncio
    async def test_json_toggle_success(self, mock_redis_connection_manager):
        """Test successful JSON toggle operation."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.toggle = AsyncMock(return_value=True)

        result = await json_toggle("test_doc", ".flag")

        mock_redis.json.return_value.toggle.assert_called_once_with("test_doc", ".flag")
        assert "Boolean toggled. New state at '.flag': True" in result

    @pytest.mark.asyncio
    async def test_json_toggle_error(self, mock_redis_connection_manager):
        """Test JSON toggle with Redis error."""
        mock_redis = mock_redis_connection_manager
        mock_redis.json.return_value.toggle = AsyncMock(
            side_effect=RedisError("Not boolean")
        )

        result = await json_toggle("test_doc", ".flag")
        assert "Error toggling boolean at '.flag' in 'test_doc': Not boolean" in result
