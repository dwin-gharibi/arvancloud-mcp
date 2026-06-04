"""Opt-in live integration tests against the real ArvanCloud API.

These run only when ARVAN_API_KEY is set (otherwise skipped). They make
read-only calls so they're safe to run against a real account:

    ARVAN_API_KEY='Apikey ...' pytest tests/live -q
"""

from __future__ import annotations

import os

import pytest

from arvancloud_mcp.client import ArvanClient
from arvancloud_mcp.config import Settings

pytestmark = pytest.mark.skipif(
    not os.getenv("ARVAN_API_KEY"),
    reason="set ARVAN_API_KEY to run live integration tests",
)


async def test_live_list_regions():
    async with ArvanClient(Settings.from_env()) as client:
        data = await client.request("GET", "/ecc/v1/regions")
    assert data is not None


async def test_live_list_domains():
    async with ArvanClient(Settings.from_env()) as client:
        data = await client.request("GET", "/cdn/4.0/domains")
    assert data is not None
