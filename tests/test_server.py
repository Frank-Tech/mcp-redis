"""
Unit tests for src/common/server.py
"""

import importlib
from unittest.mock import patch

from fastmcp import FastMCP
from src.common.server import mcp


class TestMCPServer:
    """Test cases for MCP server initialization."""

    def test_mcp_server_instance_exists(self):
        """Test that mcp server instance is created."""
        assert mcp is not None
        assert hasattr(mcp, "run")
        assert hasattr(mcp, "tool")

    def test_mcp_server_name(self):
        """Test that mcp server has correct name."""
        # Verify it is the correct class instance
        assert isinstance(mcp, FastMCP)
        # Verify the name attribute (FastMCP usually stores this)
        assert mcp.name == "Redis MCP Server"

    def test_mcp_server_dependencies(self):
        """Test that mcp server instance exists."""
        # Note: 'dependencies' argument was removed in the new implementation,
        # so we just verify the instance is valid.
        assert mcp is not None

    @patch("fastmcp.FastMCP")
    def test_mcp_server_initialization(self, mock_fastmcp):
        """Test MCP server initialization with correct parameters."""
        # Re-import to trigger initialization
        import src.common.server

        importlib.reload(src.common.server)

        # Verify FastMCP was called with correct parameters (No dependencies list)
        mock_fastmcp.assert_called_once_with("Redis MCP Server")

    def test_mcp_server_tool_decorator(self):
        """Test that mcp server provides tool decorator."""
        assert hasattr(mcp, "tool")
        assert callable(mcp.tool)

    def test_mcp_server_run_method(self):
        """Test that mcp server provides run method."""
        assert hasattr(mcp, "run")
        assert callable(mcp.run)

    @patch.object(mcp, "run")
    def test_mcp_server_run_can_be_called(self, mock_run):
        """Test that mcp server run method can be called."""
        mcp.run()
        mock_run.assert_called_once()

    def test_mcp_tool_decorator_functionality(self):
        """Test that the tool decorator can be used."""

        # Test that we can use the decorator
        @mcp.tool()
        async def test_tool():
            """Test tool for decorator functionality."""
            return "test"

        # Verify the decorator worked (relies on conftest patch for .fn/attributes)
        assert callable(test_tool)
        # If using the 'pass_through_tool' patch, __name__ is preserved
        if hasattr(test_tool, "__name__"):
            assert test_tool.__name__ == "test_tool"

    def test_mcp_tool_decorator_with_parameters(self):
        """Test that the tool decorator works with parameters."""

        @mcp.tool()
        async def test_tool_with_params(param1: str, param2: int = 10):
            """Test tool with parameters."""
            return f"{param1}:{param2}"

        # Verify the decorator worked
        assert callable(test_tool_with_params)

    def test_mcp_server_is_singleton(self):
        """Test that importing server multiple times returns same instance."""
        from src.common.server import mcp as mcp1
        from src.common.server import mcp as mcp2

        assert mcp1 is mcp2
        assert id(mcp1) == id(mcp2)

    @patch("fastmcp.FastMCP")
    def test_mcp_server_init_args(self, mock_fastmcp):
        """Test that MCP server is initialized without legacy dependencies."""
        # Re-import to trigger initialization
        import src.common.server

        importlib.reload(src.common.server)

        # Get the call arguments
        args, kwargs = mock_fastmcp.call_args

        # Assert Name
        assert args[0] == "Redis MCP Server"

        # Assert dependencies are NOT passed (since they were removed in source)
        assert "dependencies" not in kwargs

    def test_mcp_server_type(self):
        """Test that mcp server is of correct type."""
        assert isinstance(mcp, FastMCP)

    def test_mcp_server_attributes(self):
        """Test that mcp server has expected attributes."""
        # Test for common FastMCP attributes
        expected_attributes = ["run", "tool"]

        for attr in expected_attributes:
            assert hasattr(mcp, attr), f"MCP server missing attribute: {attr}"
            assert callable(getattr(mcp, attr)), (
                f"MCP server attribute {attr} is not callable"
            )
