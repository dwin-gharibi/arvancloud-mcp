"""Remote execution tools — SSH into a server and run commands / transfer files.

This is what turns the server into an end-to-end workflow: provision a VM with
the compute tools, then connect over SSH to run setup commands, deploy code, or
inspect the box. Built on asyncssh.

Connection defaults come from settings (``ARVAN_SSH_USER``, ``ARVAN_SSH_KEY`` /
``ARVAN_SSH_KEY_FILE``, ``ARVAN_SSH_PASSWORD``, ``ARVAN_SSH_PORT``) and can be
overridden per call. Host-key verification is disabled by default because
freshly provisioned servers aren't in any known_hosts file; point
``ARVAN_SSH_KNOWN_HOSTS`` at a file (or pass ``known_hosts``) to enforce it.
"""

from __future__ import annotations

import base64
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient

_MAX_INLINE_BYTES = 256 * 1024


def register(mcp: FastMCP, client: ArvanClient) -> None:
    settings = client.settings

    def _connect_kwargs(
        host: str,
        username: str | None,
        port: int | None,
        private_key: str | None,
        key_file: str | None,
        password: str | None,
        passphrase: str | None,
        known_hosts: str | None,
        connect_timeout: float | None,
    ) -> dict[str, Any]:
        import asyncssh

        kwargs: dict[str, Any] = {
            "host": host,
            "port": port or settings.ssh_port or 22,
            "username": username or settings.ssh_user or "root",
            "connect_timeout": connect_timeout or settings.ssh_timeout or 30.0,
        }
        kh = known_hosts if known_hosts is not None else settings.ssh_known_hosts
        kwargs["known_hosts"] = kh or None

        client_keys: list[Any] = []
        pk = private_key if private_key is not None else settings.ssh_key
        kf = key_file if key_file is not None else settings.ssh_key_file
        if pk:
            client_keys.append(asyncssh.import_private_key(pk, passphrase or None))
        elif kf:
            client_keys.append(kf)
        if client_keys:
            kwargs["client_keys"] = client_keys

        pw = password if password is not None else settings.ssh_password
        if pw:
            kwargs["password"] = pw
        return kwargs

    async def _connect(**kwargs: Any):
        import asyncssh

        try:
            return await asyncssh.connect(**kwargs)
        except (asyncssh.Error, OSError) as exc:
            raise RuntimeError(f"SSH connection to {kwargs.get('host')} failed: {exc}") from exc

    @mcp.tool()
    async def arvan_ssh_run(
        host: str,
        command: str,
        username: str | None = None,
        port: int | None = None,
        private_key: str | None = None,
        key_file: str | None = None,
        password: str | None = None,
        passphrase: str | None = None,
        known_hosts: str | None = None,
        connect_timeout: float | None = None,
        command_timeout: float | None = None,
    ) -> Any:
        """Run a single command on a server over SSH and return its output.

        Args:
            host: Server IP or hostname (e.g. a freshly created server's public IP).
            command: The shell command to execute.
            username: SSH user (defaults to ARVAN_SSH_USER, typically ``root``).
            port: SSH port (default 22).
            private_key: Inline PEM private key (overrides the configured default).
            key_file: Path to a private key file.
            password: Password auth (if not using a key).
            passphrase: Passphrase for an encrypted private key.
            known_hosts: Path to a known_hosts file; omit to skip host-key checks.
            connect_timeout: Seconds to wait for the connection.
            command_timeout: Seconds to wait for the command to finish.

        Returns:
            ``{exit_status, stdout, stderr, host}``.
        """

        import asyncssh

        kwargs = _connect_kwargs(
            host, username, port, private_key, key_file, password,
            passphrase, known_hosts, connect_timeout,
        )
        conn = await _connect(**kwargs)
        try:
            result = await conn.run(command, check=False, timeout=command_timeout)
        except asyncssh.Error as exc:
            raise RuntimeError(f"SSH command failed: {exc}") from exc
        finally:
            conn.close()
        return {
            "host": host,
            "exit_status": result.exit_status,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    @mcp.tool()
    async def arvan_ssh_run_script(
        host: str,
        script: str,
        username: str | None = None,
        port: int | None = None,
        private_key: str | None = None,
        key_file: str | None = None,
        password: str | None = None,
        passphrase: str | None = None,
        known_hosts: str | None = None,
        connect_timeout: float | None = None,
        command_timeout: float | None = None,
        interpreter: str = "bash -s",
    ) -> Any:
        """Run a multi-line script on a server over SSH (piped to ``bash -s``).

        Use this for setup/bootstrap scripts. ``interpreter`` can be changed to,
        e.g., ``sh -s`` or ``python3 -``.
        """

        import asyncssh

        kwargs = _connect_kwargs(
            host, username, port, private_key, key_file, password,
            passphrase, known_hosts, connect_timeout,
        )
        conn = await _connect(**kwargs)
        try:
            result = await conn.run(
                interpreter, input=script, check=False, timeout=command_timeout
            )
        except asyncssh.Error as exc:
            raise RuntimeError(f"SSH script failed: {exc}") from exc
        finally:
            conn.close()
        return {
            "host": host,
            "exit_status": result.exit_status,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    @mcp.tool()
    async def arvan_ssh_upload_file(
        host: str,
        remote_path: str,
        content: str,
        content_base64: bool = False,
        username: str | None = None,
        port: int | None = None,
        private_key: str | None = None,
        key_file: str | None = None,
        password: str | None = None,
        passphrase: str | None = None,
        known_hosts: str | None = None,
    ) -> Any:
        """Write content to a file on the server via SFTP.

        ``content`` is plain text, or base64 when ``content_base64`` is set.
        """

        import asyncssh

        data = base64.b64decode(content) if content_base64 else content.encode("utf-8")
        kwargs = _connect_kwargs(
            host, username, port, private_key, key_file, password,
            passphrase, known_hosts, None,
        )
        conn = await _connect(**kwargs)
        try:
            async with conn.start_sftp_client() as sftp:
                async with sftp.open(remote_path, "wb") as f:
                    await f.write(data)
        except asyncssh.Error as exc:
            raise RuntimeError(f"SFTP upload failed: {exc}") from exc
        finally:
            conn.close()
        return {"host": host, "remote_path": remote_path, "bytes": len(data)}

    @mcp.tool()
    async def arvan_ssh_download_file(
        host: str,
        remote_path: str,
        as_base64: bool = False,
        username: str | None = None,
        port: int | None = None,
        private_key: str | None = None,
        key_file: str | None = None,
        password: str | None = None,
        passphrase: str | None = None,
        known_hosts: str | None = None,
    ) -> Any:
        """Read a file from the server via SFTP (truncated to 256 KiB)."""

        import asyncssh

        kwargs = _connect_kwargs(
            host, username, port, private_key, key_file, password,
            passphrase, known_hosts, None,
        )
        conn = await _connect(**kwargs)
        try:
            async with conn.start_sftp_client() as sftp:
                async with sftp.open(remote_path, "rb") as f:
                    raw = await f.read(_MAX_INLINE_BYTES + 1)
        except asyncssh.Error as exc:
            raise RuntimeError(f"SFTP download failed: {exc}") from exc
        finally:
            conn.close()

        truncated = len(raw) > _MAX_INLINE_BYTES
        raw = raw[:_MAX_INLINE_BYTES]
        out: dict[str, Any] = {"host": host, "remote_path": remote_path, "truncated": truncated}
        if as_base64:
            out["content_base64"] = base64.b64encode(raw).decode("ascii")
        else:
            try:
                out["content"] = raw.decode("utf-8")
            except UnicodeDecodeError:
                out["content_base64"] = base64.b64encode(raw).decode("ascii")
                out["note"] = "binary content returned as base64"
        return out

    @mcp.tool()
    async def arvan_ssh_check_connection(
        host: str,
        username: str | None = None,
        port: int | None = None,
        private_key: str | None = None,
        key_file: str | None = None,
        password: str | None = None,
        passphrase: str | None = None,
        known_hosts: str | None = None,
        connect_timeout: float | None = None,
    ) -> Any:
        """Verify SSH connectivity/auth to a server (useful after provisioning).

        Returns whether the connection succeeded and the server's SSH banner.
        """

        kwargs = _connect_kwargs(
            host, username, port, private_key, key_file, password,
            passphrase, known_hosts, connect_timeout,
        )
        conn = await _connect(**kwargs)
        try:
            server_version = conn.get_extra_info("server_version")
        finally:
            conn.close()
        return {"host": host, "connected": True, "server_version": server_version}
