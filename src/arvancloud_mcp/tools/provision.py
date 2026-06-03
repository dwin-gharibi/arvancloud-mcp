"""High-level provisioning — create a server and configure it in one call.

``arvan_provision_server`` ties together the compute API and SSH: it can
generate an SSH key, register it, create the server, wait for it to boot, then
SSH in to install packages / Docker / run a setup script — returning everything
(including a generated private key) so the box is ready to use immediately.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import stat
import tempfile
import time
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ArvanAPIError, ArvanClient
from ._base import compact, resolve_region
from ._exec import run_command

_READY_STATES = {"active", "running", "up", "started"}


def _iter_strings(obj: Any):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _iter_strings(v)


def _extract_public_ip(details: Any) -> str | None:
    """Best-effort: find a public IPv4 anywhere in the server details."""

    public: list[str] = []
    private: list[str] = []
    for s in _iter_strings(details):
        try:
            ip = ipaddress.ip_address(s)
        except ValueError:
            continue
        if ip.version != 4 or ip.is_loopback or ip.is_unspecified:
            continue
        (private if ip.is_private else public).append(str(ip))
    if public:
        return public[0]
    return private[0] if private else None


def _build_setup_script(
    packages: list[str] | None, install_docker: bool, setup_script: str | None
) -> str | None:
    parts = ["#!/usr/bin/env bash", "set -euxo pipefail", "export DEBIAN_FRONTEND=noninteractive"]
    did_something = False
    if packages or install_docker:
        parts.append("apt-get update -y || true")
    if packages:
        parts.append("apt-get install -y " + " ".join(packages))
        did_something = True
    if install_docker:
        parts.append("curl -fsSL https://get.docker.com | sh")
        parts.append("systemctl enable --now docker || true")
        did_something = True
    if setup_script:
        parts.append(setup_script)
        did_something = True
    return "\n".join(parts) + "\n" if did_something else None


async def _wait_tcp(host: str, port: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            _r, w = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=5.0
            )
            w.close()
            return True
        except (OSError, asyncio.TimeoutError):
            await asyncio.sleep(5.0)
    return False


def register(mcp: FastMCP, client: ArvanClient) -> None:
    settings = client.settings

    async def _ssh_run_script(
        host: str, script: str, username: str, private_key: str | None,
        password: str | None, port: int, timeout: float,
    ) -> dict:
        import asyncssh

        connect_kwargs: dict[str, Any] = {
            "host": host, "port": port, "username": username,
            "known_hosts": None, "connect_timeout": 30.0,
        }
        if private_key:
            connect_kwargs["client_keys"] = [asyncssh.import_private_key(private_key)]
        if password:
            connect_kwargs["password"] = password
        try:
            conn = await asyncssh.connect(**connect_kwargs)
        except (asyncssh.Error, OSError) as exc:
            return {"ok": False, "error": f"ssh connect failed: {exc}"}
        try:
            result = await conn.run("bash -s", input=script, check=False, timeout=timeout)
        finally:
            conn.close()
        return {
            "ok": result.exit_status == 0,
            "exit_status": result.exit_status,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    @mcp.tool()
    async def arvan_provision_server(
        name: str,
        flavor_id: str,
        image_id: str,
        region: str | None = None,
        disk_size: int = 25,
        networks: list[str] | None = None,
        security_group_names: list[str] | None = None,
        ssh_public_key: str | None = None,
        ssh_key_name: str | None = None,
        generate_ssh_key: bool = True,
        ssh_user: str | None = None,
        ssh_password: str | None = None,
        packages: list[str] | None = None,
        install_docker: bool = False,
        setup_script: str | None = None,
        init_script: str | None = None,
        wait_timeout: float = 480.0,
        host_override: str | None = None,
    ) -> Any:
        """Provision a server and (optionally) configure it, in one call.

        Supports several configuration methods (combine as needed):
        * ``init_script`` — cloud-init that runs at first boot (no SSH needed).
        * ``packages`` / ``install_docker`` / ``setup_script`` — run over SSH
          after boot (builds and runs a ``bash`` script).
        For Terraform-based provisioning use the ``arvan_iac_terraform_*`` tools;
        for Kubernetes use the ``arvan_k8s_*`` / ``arvan_helm_*`` tools.

        Steps: register/generate an SSH key, create the server (optionally with
        cloud-init), wait for boot, detect its public IP, then SSH in and run the
        install script built from ``packages`` / ``install_docker`` / ``setup_script``.

        Args:
            name: Server name.
            flavor_id: Plan id (see ``arvan_list_plans``).
            image_id: Image id (see ``arvan_list_images``).
            region: Region; defaults to ARVAN_DEFAULT_REGION.
            disk_size: Root disk size (GB).
            networks: Network ids to attach (include a public network for SSH).
            security_group_names: Security groups to apply.
            ssh_public_key: Existing public key to inject. If omitted and
                ``generate_ssh_key`` is true, a new ed25519 keypair is generated
                and the private key is returned (store it securely!).
            ssh_key_name: Name to register the key under (default ``<name>-key``).
            generate_ssh_key: Generate a keypair when no public key is given.
            ssh_user: SSH user for the install step (default ARVAN_SSH_USER/root).
            ssh_password: Use password auth for the install step instead of a key.
            packages: apt packages to install.
            install_docker: Install Docker via get.docker.com.
            setup_script: Extra shell commands to run after package install.
            wait_timeout: Max seconds to wait for boot + SSH availability.
            host_override: Use this IP/host for SSH instead of auto-detection.

        Returns a summary with the server details, public IP, SSH info (incl. any
        generated private key), and install output.
        """

        region = resolve_region(client, region)
        summary: dict[str, Any] = {"region": region, "steps": []}
        private_key: str | None = None

        key_name = ssh_key_name
        if not ssh_public_key and generate_ssh_key and not ssh_password:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import ed25519

            k = ed25519.Ed25519PrivateKey.generate()
            private_key = k.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.OpenSSH,
                serialization.NoEncryption(),
            ).decode()
            ssh_public_key = (
                k.public_key()
                .public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)
                .decode()
                + f" {name}"
            )
            summary["steps"].append("generated ed25519 keypair")

        if ssh_public_key:
            key_name = key_name or f"{name}-key"
            try:
                await client.request(
                    "POST",
                    f"/ecc/v1/regions/{region}/ssh-keys",
                    json={"name": key_name, "public_key": ssh_public_key},
                )
                summary["steps"].append(f"registered ssh key '{key_name}'")
            except ArvanAPIError as exc:
                summary["steps"].append(f"ssh key register skipped: {exc}")

        body: dict[str, Any] = compact(
            {
                "name": name,
                "flavor_id": flavor_id,
                "image_id": image_id,
                "disk_size": disk_size,
                "count": 1,
                "network_ids": networks,
                "ha_enabled": False,
                "init_script": init_script,
            }
        )
        if security_group_names:
            body["security_groups"] = [{"name": n} for n in security_group_names]
        if key_name:
            body["ssh_key"] = True
            body["key_name"] = key_name
        created = await client.request(
            "POST", f"/ecc/v1/regions/{region}/servers", json=body
        )
        summary["server_create"] = created
        summary["steps"].append("server create requested")

        data = created.get("data", created) if isinstance(created, dict) else created
        server = data[0] if isinstance(data, list) and data else data
        server_id = server.get("id") if isinstance(server, dict) else None
        summary["server_id"] = server_id

        details: Any = server
        if server_id:
            deadline = time.monotonic() + min(wait_timeout, 1800.0)
            while True:
                got = await client.request(
                    "GET", f"/ecc/v1/regions/{region}/servers/{server_id}"
                )
                details = got.get("data", got) if isinstance(got, dict) else got
                status = (details.get("status") if isinstance(details, dict) else "") or ""
                if status.lower() in _READY_STATES or time.monotonic() >= deadline:
                    summary["status"] = status
                    break
                await asyncio.sleep(8.0)
        summary["server"] = details

        public_ip = host_override or _extract_public_ip(details)
        summary["public_ip"] = public_ip

        script = _build_setup_script(packages, install_docker, setup_script)
        if script and public_ip and (private_key or ssh_password):
            reachable = await _wait_tcp(public_ip, 22, min(wait_timeout, 300.0))
            if not reachable:
                summary["install"] = {"ok": False, "error": "SSH port 22 not reachable in time"}
            else:
                summary["install"] = await _ssh_run_script(
                    host=public_ip,
                    script=script,
                    username=ssh_user or settings.ssh_user or "root",
                    private_key=private_key,
                    password=ssh_password or None,
                    port=settings.ssh_port or 22,
                    timeout=max(wait_timeout, 600.0),
                )
            summary["steps"].append("ran install script over SSH")
        elif script:
            summary["install"] = {
                "ok": False,
                "skipped": True,
                "reason": "need a public IP and SSH auth (generated key or password)",
            }

        if private_key:
            summary["ssh_private_key"] = private_key
            summary["warning"] = (
                "A private key was generated and is returned ONCE here — store it "
                "securely; it is not saved anywhere."
            )
        summary["ssh_user"] = ssh_user or settings.ssh_user or "root"
        summary["ssh_key_name"] = key_name
        return summary

    @mcp.tool()
    async def arvan_ansible_playbook(
        host: str,
        playbook: str,
        ssh_user: str | None = None,
        private_key: str | None = None,
        key_file: str | None = None,
        ssh_port: int | None = None,
        become: bool = False,
        extra_vars: dict[str, Any] | None = None,
        timeout: float = 900.0,
    ) -> Any:
        """Run an Ansible playbook against a host (requires ``ansible-playbook``).

        ``playbook`` is the YAML content. Auth/host default to the SSH settings.
        Host-key checking is disabled (fresh servers).
        """

        user = ssh_user or settings.ssh_user or "root"
        port = ssh_port or settings.ssh_port or 22
        key = private_key if private_key is not None else settings.ssh_key
        kf = key_file if key_file is not None else settings.ssh_key_file

        with tempfile.TemporaryDirectory(prefix="arvan-ansible-") as tmp:
            pb_path = os.path.join(tmp, "playbook.yml")
            with open(pb_path, "w", encoding="utf-8") as fh:
                fh.write(playbook)

            inv_line = (
                f"{host} ansible_host={host} ansible_user={user} ansible_port={port}"
            )
            if key:
                key_path = os.path.join(tmp, "id_key")
                with open(key_path, "w", encoding="utf-8") as fh:
                    fh.write(key if key.endswith("\n") else key + "\n")
                os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
                inv_line += f" ansible_ssh_private_key_file={key_path}"
            elif kf:
                inv_line += f" ansible_ssh_private_key_file={kf}"

            inv_path = os.path.join(tmp, "inventory.ini")
            with open(inv_path, "w", encoding="utf-8") as fh:
                fh.write(f"[all]\n{inv_line}\n")

            cmd = ["ansible-playbook", "-i", inv_path, pb_path]
            if become:
                cmd.append("--become")
            if extra_vars:
                cmd += ["--extra-vars", json.dumps(extra_vars)]
            return await run_command(
                cmd,
                cwd=tmp,
                timeout=timeout,
                env_extra={"ANSIBLE_HOST_KEY_CHECKING": "False"},
            )
