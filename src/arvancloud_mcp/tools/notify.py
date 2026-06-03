"""Notification integrations — Slack, Telegram, generic webhook, and email.

Handy for announcing results of long jobs (pair with the tasks scheduler) or
alerting on findings (pair with the security audits).
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient


def register(mcp: FastMCP, client: ArvanClient) -> None:
    @mcp.tool()
    async def arvan_notify_slack(text: str, webhook_url: str | None = None) -> Any:
        """Post a message to a Slack incoming webhook.

        ``webhook_url`` falls back to the SLACK_WEBHOOK_URL environment variable.
        """

        url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        if not url:
            return {"ok": False, "error": "no Slack webhook URL (set SLACK_WEBHOOK_URL)"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as hc:
                resp = await hc.post(url, json={"text": text})
            return {"ok": resp.status_code < 400, "status_code": resp.status_code}
        except httpx.HTTPError as exc:
            return {"ok": False, "error": str(exc)}

    @mcp.tool()
    async def arvan_notify_telegram(
        text: str,
        chat_id: str | None = None,
        bot_token: str | None = None,
    ) -> Any:
        """Send a Telegram message via a bot.

        ``bot_token``/``chat_id`` fall back to TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID.
        """

        token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        chat = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat:
            return {"ok": False, "error": "need bot_token and chat_id (or env vars)"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as hc:
                resp = await hc.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat, "text": text},
                )
            return {"ok": resp.status_code < 400, "status_code": resp.status_code}
        except httpx.HTTPError as exc:
            return {"ok": False, "error": str(exc)}

    @mcp.tool()
    async def arvan_notify_webhook(
        url: str, payload: dict[str, Any] | None = None, text: str | None = None
    ) -> Any:
        """POST a JSON payload (or ``{"text": ...}``) to an arbitrary webhook."""

        body = payload if payload is not None else {"text": text or ""}
        try:
            async with httpx.AsyncClient(timeout=15.0) as hc:
                resp = await hc.post(url, json=body)
            return {"ok": resp.status_code < 400, "status_code": resp.status_code}
        except httpx.HTTPError as exc:
            return {"ok": False, "error": str(exc)}

    @mcp.tool()
    async def arvan_notify_email(
        to: str,
        subject: str,
        body: str,
        from_addr: str | None = None,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        use_tls: bool = True,
    ) -> Any:
        """Send an email via SMTP.

        SMTP settings fall back to ARVAN_SMTP_HOST/PORT/USER/PASSWORD/FROM env vars.
        """

        host = smtp_host or os.getenv("ARVAN_SMTP_HOST")
        port = smtp_port or int(os.getenv("ARVAN_SMTP_PORT", "587"))
        user = smtp_user or os.getenv("ARVAN_SMTP_USER")
        password = smtp_password or os.getenv("ARVAN_SMTP_PASSWORD")
        sender = from_addr or os.getenv("ARVAN_SMTP_FROM") or user
        if not host or not sender:
            return {"ok": False, "error": "SMTP not configured (set ARVAN_SMTP_HOST/FROM)"}

        def _send() -> dict:
            import smtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg["From"] = sender
            msg["To"] = to
            msg["Subject"] = subject
            msg.set_content(body)
            try:
                with smtplib.SMTP(host, port, timeout=30) as server:
                    if use_tls:
                        server.starttls()
                    if user and password:
                        server.login(user, password)
                    server.send_message(msg)
                return {"ok": True, "to": to}
            except Exception as exc:
                return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

        return await asyncio.to_thread(_send)
