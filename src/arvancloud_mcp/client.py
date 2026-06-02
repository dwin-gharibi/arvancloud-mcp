"""Async HTTP client for the ArvanCloud unified API.

Handles authentication (``Authorization: Apikey <key>``), JSON encoding,
transient-failure retries with exponential backoff, and consistent error
reporting. Every product module in :mod:`arvancloud_mcp.tools` is built on
top of this client.
"""

from __future__ import annotations

import asyncio
import json as _json
from typing import Any, Mapping

import httpx

from .config import Settings

_RETRY_STATUS = {429, 500, 502, 503, 504}


class ArvanAPIError(Exception):
    """Raised when the ArvanCloud API returns an error or is unreachable.

    The string representation is intentionally compact and human readable so
    it can be surfaced directly to an MCP client.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        method: str | None = None,
        path: str | None = None,
        details: Any = None,
    ) -> None:
        self.status_code = status_code
        self.method = method
        self.path = path
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        prefix = ""
        if self.method and self.path:
            prefix = f"{self.method} {self.path} -> "
        if self.status_code:
            prefix += f"HTTP {self.status_code}: "
        base = prefix + (self.args[0] if self.args else "request failed")
        if self.details not in (None, "", {}, []):
            try:
                base += f" | details: {_json.dumps(self.details, ensure_ascii=False)}"
            except (TypeError, ValueError):
                base += f" | details: {self.details}"
        return base


def _clean_params(params: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Drop ``None`` values and render booleans the way the API expects."""

    if not params:
        return None
    cleaned: dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            cleaned[key] = "true" if value else "false"
        else:
            cleaned[key] = value
    return cleaned or None


class ArvanClient:
    """Thin async wrapper around :class:`httpx.AsyncClient`."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: httpx.AsyncClient | None = None
        self._lock = asyncio.Lock()

    @property
    def settings(self) -> Settings:
        return self._settings

    def _authorization(self) -> str:
        """Normalise the API key into a valid ``Authorization`` header value.

        ArvanCloud expects ``Apikey <token>`` (note the capital ``A``). Users
        commonly paste either the bare token or the whole ``apikey ...`` string
        copied from the panel, so we accept both.
        """

        key = (self._settings.api_key or "").strip()
        if not key:
            return ""
        if key.lower().startswith("apikey "):
            token = key[len("apikey ") :].strip()
            return f"Apikey {token}"
        return f"Apikey {key}"

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    headers = {
                        "Accept": "application/json",
                        "User-Agent": self._settings.user_agent,
                    }
                    auth = self._authorization()
                    if auth:
                        headers["Authorization"] = auth
                    self._client = httpx.AsyncClient(
                        base_url=self._settings.base_url,
                        timeout=self._settings.timeout,
                        headers=headers,
                        verify=self._settings.verify_ssl,
                        follow_redirects=True,
                    )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "ArvanClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        files: Any = None,
        data: Any = None,
        raw: bool = False,
    ) -> Any:
        """Perform an authenticated request and return the decoded body.

        ``path`` is relative to the configured base URL (a leading slash is
        optional). Provide ``json`` for a JSON body, or ``files``/``data`` for a
        multipart upload. On a 2xx response the parsed JSON body is returned (or
        the raw text when ``raw=True``); anything else raises
        :class:`ArvanAPIError`. Network errors and retryable status codes are
        retried with exponential backoff according to the configured
        ``max_retries``/``backoff_factor``.
        """

        if not self._settings.api_key:
            raise ArvanAPIError(
                "No API key configured. Set ARVAN_API_KEY to a machine-user "
                "access key created in the ArvanCloud panel.",
                method=method.upper(),
                path=path,
            )

        client = await self._ensure_client()
        url = path if path.startswith("/") else f"/{path}"
        clean_params = _clean_params(params)

        request_kwargs: dict[str, Any] = {"params": clean_params}
        if files is not None or data is not None:
            if files is not None:
                request_kwargs["files"] = files
            if data is not None:
                request_kwargs["data"] = data
        elif json is not None:
            request_kwargs["json"] = json

        attempt = 0
        while True:
            try:
                response = await client.request(
                    method.upper(), url, **request_kwargs
                )
            except httpx.TimeoutException as exc:
                if attempt < self._settings.max_retries:
                    await self._sleep(attempt)
                    attempt += 1
                    continue
                raise ArvanAPIError(
                    f"request timed out after {self._settings.max_retries} retries: {exc}",
                    method=method.upper(),
                    path=url,
                ) from exc
            except httpx.TransportError as exc:
                if attempt < self._settings.max_retries:
                    await self._sleep(attempt)
                    attempt += 1
                    continue
                raise ArvanAPIError(
                    f"network error: {exc}",
                    method=method.upper(),
                    path=url,
                ) from exc

            if (
                response.status_code in _RETRY_STATUS
                and attempt < self._settings.max_retries
            ):
                await self._sleep(attempt, response)
                attempt += 1
                continue

            return self._handle_response(response, method.upper(), url, raw)

    async def _sleep(self, attempt: int, response: httpx.Response | None = None) -> None:
        """Sleep before a retry, honouring ``Retry-After`` when present."""

        delay = self._settings.backoff_factor * (2 ** attempt)
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    delay = max(delay, float(retry_after))
                except ValueError:
                    pass
        await asyncio.sleep(min(delay, 30.0))

    def _handle_response(
        self, response: httpx.Response, method: str, path: str, raw: bool
    ) -> Any:
        if raw:
            if response.status_code >= 400:
                raise ArvanAPIError(
                    response.text or response.reason_phrase,
                    status_code=response.status_code,
                    method=method,
                    path=path,
                )
            return response.text

        body: Any = None
        if response.content:
            try:
                body = response.json()
            except ValueError:
                body = response.text

        if response.status_code >= 400:
            message = response.reason_phrase or "request failed"
            details: Any = body
            if isinstance(body, dict):
                message = (
                    body.get("message")
                    or body.get("error")
                    or body.get("detail")
                    or message
                )
                details = body.get("errors") or body.get("data") or body
            raise ArvanAPIError(
                message,
                status_code=response.status_code,
                method=method,
                path=path,
                details=details,
            )

        if body is None:
            return {"status": response.status_code, "ok": True}
        return body
