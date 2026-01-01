from unittest.mock import patch


def _pass_through_tool(*args, **kwargs):
    def wrapper(func):
        func.fn = func
        return func

    return wrapper


patcher = patch("fastmcp.FastMCP.tool", side_effect=_pass_through_tool)
patcher.start()

import pytest  # noqa


@pytest.fixture(scope="session", autouse=True)
def stop_tool_patch():
    yield
    patcher.stop()
