import pytest

import src.tools.misc as misc


@pytest.mark.asyncio
async def test_execute_command_success_decoding(monkeypatch):
    """
    Ensure execute_command runs successfully and recursively decodes
    bytes to strings (including nested lists).
    """

    class DummyRedis:
        async def execute_command(self, command, *args):
            return [b"result1", 42, [b"nested_key", b"nested_val"]]

    monkeypatch.setattr(
        misc.RedisConnectionManager, "get_connection", lambda: DummyRedis()
    )

    result = await misc.execute_command("SOME.CMD", ["arg1"])

    assert result == ["result1", 42, ["nested_key", "nested_val"]]


@pytest.mark.asyncio
async def test_execute_command_redis_error(monkeypatch):
    """Ensure execute_command catches RedisError and returns a formatted error string."""

    class DummyRedis:
        async def execute_command(self, command, *args):
            raise misc.RedisError("Invalid syntax")

    monkeypatch.setattr(
        misc.RedisConnectionManager, "get_connection", lambda: DummyRedis()
    )

    result = await misc.execute_command("BAD.CMD")

    assert isinstance(result, str)
    assert result.startswith("Error executing command 'BAD.CMD'")
    assert "Invalid syntax" in result


@pytest.mark.asyncio
async def test_search_redis_documents_url_not_configured(monkeypatch):
    """Return a clear error if MCP_DOCS_SEARCH_URL is not set for search_redis_documents."""
    monkeypatch.setattr(misc, "MCP_DOCS_SEARCH_URL", "")

    result = await misc.search_redis_documents("What is Redis?")

    assert isinstance(result, dict)
    assert (
        result["error"] == "MCP_DOCS_SEARCH_URL environment variable is not configured"
    )


@pytest.mark.asyncio
async def test_search_redis_documents_empty_question(monkeypatch):
    """Reject empty/whitespace-only questions for search_redis_documents."""
    monkeypatch.setattr(misc, "MCP_DOCS_SEARCH_URL", "https://example.com/docs")

    result = await misc.search_redis_documents("   ")

    assert isinstance(result, dict)
    assert result["error"] == "Question parameter cannot be empty"


@pytest.mark.asyncio
async def test_search_redis_documents_success_json_response(monkeypatch):
    """Return parsed JSON when the docs API responds with JSON for search_redis_documents."""

    class DummyResponse:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def json(self):
            return {"results": [{"title": "Redis Intro"}]}

    class DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, *_, **__):  # pragma: no cover - trivial wrapper
            return DummyResponse()

    monkeypatch.setattr(misc, "MCP_DOCS_SEARCH_URL", "https://example.com/docs")
    monkeypatch.setattr(misc.aiohttp, "ClientSession", DummySession)

    result = await misc.search_redis_documents("What is a Redis stream?")

    assert isinstance(result, dict)
    assert result["results"][0]["title"] == "Redis Intro"


@pytest.mark.asyncio
async def test_search_redis_documents_non_json_response(monkeypatch):
    """If the response is not JSON, surface the text content in an error from search_redis_documents."""

    class DummyContentTypeError(Exception):
        pass

    class DummyResponse:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def json(self):
            raise DummyContentTypeError("Not JSON")

        async def text(self):
            return "<html>not json</html>"

    class DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, *_, **__):  # pragma: no cover - trivial wrapper
            return DummyResponse()

    monkeypatch.setattr(misc, "MCP_DOCS_SEARCH_URL", "https://example.com/docs")
    # Patch aiohttp.ContentTypeError to our dummy so the except block matches
    monkeypatch.setattr(misc.aiohttp, "ContentTypeError", DummyContentTypeError)
    monkeypatch.setattr(misc.aiohttp, "ClientSession", DummySession)

    result = await misc.search_redis_documents("Explain Redis JSON")

    assert isinstance(result, dict)
    assert "Non-JSON response" in result["error"]
    assert "not json" in result["error"]


@pytest.mark.asyncio
async def test_search_redis_documents_http_client_error(monkeypatch):
    """HTTP client errors from search_redis_documents are caught and returned in an error dict."""

    class DummyClientError(Exception):
        pass

    class ErrorResponse:
        async def __aenter__(self):
            raise DummyClientError("boom")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, *_, **__):  # pragma: no cover - trivial wrapper
            return ErrorResponse()

    monkeypatch.setattr(misc, "MCP_DOCS_SEARCH_URL", "https://example.com/docs")
    monkeypatch.setattr(misc.aiohttp, "ClientError", DummyClientError)
    monkeypatch.setattr(misc.aiohttp, "ClientSession", DummySession)

    result = await misc.search_redis_documents("What is Redis?")

    assert isinstance(result, dict)
    assert result["error"] == "HTTP client error: boom"
