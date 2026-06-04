"""Shared test fixtures and helpers."""

from __future__ import annotations

import json

import pytest

from arvancloud_mcp.client import ArvanClient
from arvancloud_mcp.config import Settings

TEST_BASE_URL = "https://napi.test"


def make_settings(**overrides) -> Settings:
    """A Settings object suitable for tests (fast retries, no real host)."""

    defaults = dict(
        api_key="testkey",
        base_url=TEST_BASE_URL,
        max_retries=2,
        backoff_factor=0.0,
        default_region="ir-thr-c2",
    )
    defaults.update(overrides)
    return Settings(**defaults)


def unwrap(call_tool_result):
    """Return the payload from a ``FastMCP.call_tool`` result.

    FastMCP returns a ``(content_blocks, structured_content)`` tuple for tools
    with a typed return, but just the ``content_blocks`` list for tools annotated
    ``-> Any``. Handle both: prefer structured content, otherwise parse the JSON
    text block that carries the tool's return value.
    """

    def _maybe_result(value):
        if isinstance(value, dict) and set(value.keys()) == {"result"}:
            return value["result"]
        return value

    content = call_tool_result
    if isinstance(call_tool_result, tuple):
        structured = call_tool_result[1]
        if structured is not None:
            return _maybe_result(structured)
        content = call_tool_result[0]

    for block in content:
        text = getattr(block, "text", None)
        if text is not None:
            try:
                return _maybe_result(json.loads(text))
            except (ValueError, TypeError):
                return text
    return content


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
async def client(settings: Settings):
    c = ArvanClient(settings)
    try:
        yield c
    finally:
        await c.aclose()
