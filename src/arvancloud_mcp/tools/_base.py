"""Helpers shared by the tool modules."""

from __future__ import annotations

from typing import Any

from ..client import ArvanAPIError, ArvanClient


def resolve_region(client: ArvanClient, region: str | None) -> str:
    """Return the region to use, falling back to the configured default."""

    chosen = (region or "").strip() or (client.settings.default_region or "")
    if not chosen:
        raise ArvanAPIError(
            "No region specified. Pass region (e.g. 'ir-thr-c2') or set "
            "ARVAN_DEFAULT_REGION. Use arvan_list_regions to see options."
        )
    return chosen


def compact(data: dict[str, Any]) -> dict[str, Any]:
    """Drop ``None`` values from a request body."""

    return {k: v for k, v in data.items() if v is not None}
