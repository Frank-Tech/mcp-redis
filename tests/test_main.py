"""
Unit tests for src/main.py
"""

import logging
import asyncio
from unittest.mock import patch

import pytest
from click.testing import CliRunner

# Import explicitly to allow patch.object
import src.main
from src.main import cli, run_redis_server


class TestServerExecution:
    """Test cases for the run_redis_server function and internal modes."""

    @patch("src.main.uvicorn.run")
    def test_run_http_mode(self, mock_uvicorn_run, caplog):
        """Test that run_redis_server starts uvicorn for http transport."""
        with caplog.at_level(logging.INFO):
            run_redis_server(
                transport="http",
                mcp_host="127.0.0.1",
                mcp_port=8000,
                workers=1,
                host="redis-host",
                port=6379,
            )

        assert "Binding to TCP: 127.0.0.1:8000" in caplog.text

        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs["host"] == "127.0.0.1"
        assert call_kwargs["port"] == 8000
        assert call_kwargs["workers"] == 1

    @patch("src.main.asyncio.run")
    def test_run_stdio_mode(self, mock_asyncio_run):
        """Test that run_redis_server triggers stdio mode."""

        # 1. Run the server
        exit_code = run_redis_server(
            transport="stdio",
            mcp_host="127.0.0.1",
            mcp_port=8000,
            workers=1,
            host="localhost",
            port=6379,
        )

        assert exit_code == 0
        mock_asyncio_run.assert_called_once()

        # 2. FIX: Clean up the unawaited coroutine to suppress RuntimeWarning
        # The real code created '_run_stdio_mode()' and passed it to our mock.
        # Since the mock didn't run it, we must close it manually.
        call_args = mock_asyncio_run.call_args
        if call_args:
            coro = call_args[0][0]  # First positional argument
            if asyncio.iscoroutine(coro):
                coro.close()

    def test_stdio_mode_workers_error(self):
        """Test that stdio mode rejects multiple workers."""
        with pytest.raises(Exception) as excinfo:
            run_redis_server(
                transport="stdio",
                mcp_host="127.0.0.1",
                mcp_port=8000,
                workers=2,
                host="localhost",
                port=6379,
            )
        assert "Cannot use workers with stdio transport" in str(excinfo.value)


class TestCLI:
    """Test cases for CLI interface."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch.object(src.main, "run_redis_server")
    @patch.object(src.main, "parse_redis_uri")
    def test_cli_with_url_parameter(self, mock_parse_uri, mock_run_server):
        """Test CLI with --url parameter."""
        mock_parse_uri.return_value = {"host": "parsed-host", "port": 9999, "db": 5}

        result = self.runner.invoke(cli, ["--url", "redis://parsed-host:9999/5"])

        assert result.exit_code == 0
        mock_parse_uri.assert_called_once_with("redis://parsed-host:9999/5")

        mock_run_server.assert_called_once()
        call_kwargs = mock_run_server.call_args[1]
        assert call_kwargs["host"] == "parsed-host"
        assert call_kwargs["port"] == 9999
        assert call_kwargs["db"] == 5

    @patch.object(src.main, "run_redis_server")
    def test_cli_with_individual_parameters(self, mock_run_server):
        """Test CLI with individual connection parameters."""
        result = self.runner.invoke(
            cli,
            [
                "--transport",
                "sse",
                "--mcp-host",
                "0.0.0.0",
                "--mcp-port",
                "8080",
                "--host",
                "redis.example.com",
                "--port",
                "6380",
                "--db",
                "1",
                "--username",
                "testuser",
                "--password",
                "testpass",
                "--ssl",
                "--max-connections",
                "500",
            ],
        )

        assert result.exit_code == 0
        mock_run_server.assert_called_once()
        call_kwargs = mock_run_server.call_args[1]

        assert call_kwargs["transport"] == "sse"
        assert call_kwargs["mcp_host"] == "0.0.0.0"
        assert call_kwargs["mcp_port"] == 8080
        assert call_kwargs["host"] == "redis.example.com"
        assert call_kwargs["port"] == 6380
        assert call_kwargs["db"] == 1
        assert call_kwargs["username"] == "testuser"
        assert call_kwargs["password"] == "testpass"
        assert call_kwargs["ssl"] is True
        assert call_kwargs["max_connections"] == 500

    @patch.object(src.main, "run_redis_server")
    def test_cli_with_ssl_parameters(self, mock_run_server):
        """Test CLI with SSL-specific parameters."""
        result = self.runner.invoke(
            cli,
            [
                "--ssl",
                "--ssl-ca-path",
                "/path/to/ca.pem",
                "--ssl-keyfile",
                "/path/to/key.pem",
                "--ssl-certfile",
                "/path/to/cert.pem",
                "--ssl-cert-reqs",
                "optional",
                "--ssl-ca-certs",
                "/path/to/ca-bundle.pem",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_run_server.call_args[1]
        assert call_kwargs["ssl"] is True
        assert call_kwargs["ssl_ca_path"] == "/path/to/ca.pem"
        assert call_kwargs["ssl_keyfile"] == "/path/to/key.pem"
        assert call_kwargs["ssl_certfile"] == "/path/to/cert.pem"
        assert call_kwargs["ssl_cert_reqs"] == "optional"
        assert call_kwargs["ssl_ca_certs"] == "/path/to/ca-bundle.pem"

    # Fixed Indentation: This method is now properly inside the class
    @patch.object(src.main, "_run_stdio_mode")
    @patch.object(src.main, "run_redis_server")
    def test_cli_with_cluster_mode(self, mock_run_server, mock_stdio_mode):
        """Test CLI with cluster mode enabled."""
        result = self.runner.invoke(cli, ["--cluster-mode"])

        assert result.exit_code == 0
        call_kwargs = mock_run_server.call_args[1]
        assert call_kwargs["cluster_mode"] is True

        # Verify the internal coroutine was NOT called
        mock_stdio_mode.assert_not_called()

    @patch.object(src.main, "_run_stdio_mode")
    @patch.object(src.main, "run_redis_server")
    def test_cli_default_values(self, mock_run_server, mock_stdio_mode):
        """Test CLI with default values."""
        result = self.runner.invoke(cli, [])

        assert result.exit_code == 0
        mock_run_server.assert_called_once()
        call_kwargs = mock_run_server.call_args[1]

        assert call_kwargs["transport"] == "stdio"
        assert call_kwargs["mcp_host"] == "127.0.0.1"
        assert call_kwargs["mcp_port"] == 8000
        assert call_kwargs["host"] == "127.0.0.1"
        assert call_kwargs["port"] == 6379

        mock_stdio_mode.assert_not_called()

    @patch.object(src.main, "parse_redis_uri")
    def test_cli_with_invalid_url(self, mock_parse_uri):
        """Test CLI with invalid Redis URL."""
        mock_parse_uri.side_effect = ValueError("Invalid Redis URI")

        result = self.runner.invoke(cli, ["--url", "invalid://url"])

        assert result.exit_code != 0
        assert "Error parsing Redis URI" in result.output

    @patch.object(src.main, "run_redis_server")
    @patch.object(src.main, "parse_redis_uri")
    def test_cli_url_overrides_individual_params(self, mock_parse_uri, mock_run_server):
        """Test that --url parameter takes precedence."""
        mock_parse_uri.return_value = {"host": "uri-host", "port": 9999}

        result = self.runner.invoke(
            cli,
            [
                "--url",
                "redis://uri-host:9999/0",
                "--host",
                "individual-host",
                "--port",
                "6379",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_run_server.call_args[1]
        assert call_kwargs["host"] == "uri-host"
        assert call_kwargs["port"] == 9999

    @patch.object(src.main, "run_redis_server")
    def test_cli_server_run_failure(self, mock_run_server):
        """Test CLI when server run fails with generic exception."""
        mock_run_server.side_effect = Exception("Server run failed")

        result = self.runner.invoke(cli, [])

        assert result.exit_code != 0
        assert result.exit_code == 1

    def test_cli_help(self):
        """Test CLI help output."""
        result = self.runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "--transport" in result.output
        assert "--mcp-host" in result.output
