"""Infrastructure-as-Code validation & linting helpers.

Thin wrappers around well-known open-source tools so an agent can validate the
manifests it writes before applying them:

* terraform (fmt / validate)  - https://www.terraform.io
* tflint                       - https://github.com/terraform-linters/tflint
* checkov                      - https://github.com/bridgecrewio/checkov
* kubeconform                  - https://github.com/yannh/kubeconform
* kube-linter                  - https://github.com/stackrox/kube-linter
* hadolint (Dockerfile)        - https://github.com/hadolint/hadolint
* yamllint                     - https://github.com/adrienverge/yamllint
* trivy (config scanning)      - https://github.com/aquasecurity/trivy

Each tool runs the corresponding binary if it is installed and degrades
gracefully (``installed: false``) otherwise — install them in your image or via
the provided Dockerfile build arg. Inputs can be given inline as
``files`` (a ``{relative_path: content}`` map, written to a temp dir) or as an
existing ``directory`` path.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient
from ._exec import run_command, which
from ._exec import workspace as _workspace

_IAC_BINARIES = {
    "terraform": "terraform",
    "opentofu": "tofu",
    "terragrunt": "terragrunt",
    "tflint": "tflint",
    "tfsec": "tfsec",
    "checkov": "checkov",
    "infracost": "infracost",
    "packer": "packer",
    "kubeconform": "kubeconform",
    "kube-linter": "kube-linter",
    "hadolint": "hadolint",
    "yamllint": "yamllint",
    "trivy": "trivy",
}


def _maybe_json(result: dict) -> dict:
    """Attach a parsed JSON view of stdout when possible."""

    out = result.get("stdout")
    if out:
        try:
            result["parsed"] = json.loads(out)
        except (ValueError, TypeError):
            pass
    return result


def register(mcp: FastMCP, client: ArvanClient) -> None:
    timeout = getattr(client.settings, "iac_timeout", 120.0)

    @mcp.tool()
    async def arvan_iac_available_tools() -> Any:
        """Report which IaC validation tools are installed (and their paths)."""

        return {
            name: {"installed": which(binary) is not None, "path": which(binary)}
            for name, binary in _IAC_BINARIES.items()
        }

    @mcp.tool()
    async def arvan_iac_terraform_validate(
        files: dict[str, str] | None = None,
        directory: str | None = None,
        init: bool = True,
    ) -> Any:
        """Validate Terraform configuration (optionally ``terraform init`` first).

        ``init`` runs ``terraform init -backend=false`` so providers resolve;
        disable it for an offline syntax-only check.
        """

        with _workspace(files, directory) as workdir:
            steps: dict[str, Any] = {}
            if init:
                steps["init"] = await run_command(
                    ["terraform", "init", "-backend=false", "-input=false", "-no-color"],
                    cwd=workdir,
                    timeout=timeout,
                )
            steps["validate"] = _maybe_json(
                await run_command(
                    ["terraform", "validate", "-no-color", "-json"],
                    cwd=workdir,
                    timeout=timeout,
                )
            )
        steps["ok"] = steps["validate"].get("ok", False)
        return steps

    @mcp.tool()
    async def arvan_iac_terraform_fmt(
        files: dict[str, str] | None = None,
        directory: str | None = None,
        write: bool = False,
    ) -> Any:
        """Check (or apply, with ``write=True``) Terraform formatting."""

        cmd = ["terraform", "fmt", "-no-color", "-recursive"]
        if not write:
            cmd += ["-check", "-diff"]
        with _workspace(files, directory) as workdir:
            return await run_command(cmd, cwd=workdir, timeout=timeout)

    def _tf_env() -> dict[str, str]:
        extra: dict[str, str] = {}
        if client.settings.api_key:
            extra["TF_VAR_api_key"] = client.settings.api_key
            extra["ARVAN_API_KEY"] = client.settings.api_key
        return extra

    @mcp.tool()
    async def arvan_iac_terraform_init(
        files: dict[str, str] | None = None, directory: str | None = None
    ) -> Any:
        """Run ``terraform init`` (downloads the arvancloud/arvan provider)."""

        with _workspace(files, directory) as workdir:
            return await run_command(
                ["terraform", "init", "-input=false", "-no-color"],
                cwd=workdir,
                timeout=timeout,
                env_extra=_tf_env(),
            )

    @mcp.tool()
    async def arvan_iac_terraform_plan(
        files: dict[str, str] | None = None,
        directory: str | None = None,
        init: bool = True,
    ) -> Any:
        """Run ``terraform plan`` against the arvancloud/arvan provider.

        Use this to preview infrastructure changes before applying. The
        configured API key is injected as ``TF_VAR_api_key``/``ARVAN_API_KEY``.
        """

        with _workspace(files, directory) as workdir:
            steps: dict[str, Any] = {}
            if init:
                steps["init"] = await run_command(
                    ["terraform", "init", "-input=false", "-no-color"],
                    cwd=workdir, timeout=timeout, env_extra=_tf_env(),
                )
            steps["plan"] = await run_command(
                ["terraform", "plan", "-input=false", "-no-color"],
                cwd=workdir, timeout=timeout, env_extra=_tf_env(),
            )
            steps["ok"] = steps["plan"].get("ok", False)
            return steps

    @mcp.tool()
    async def arvan_iac_terraform_apply(
        files: dict[str, str] | None = None,
        directory: str | None = None,
        auto_approve: bool = False,
        init: bool = True,
    ) -> Any:
        """Run ``terraform apply`` to create/update real ArvanCloud infrastructure.

        This changes live infrastructure, so it refuses to run unless
        ``auto_approve=True`` is passed explicitly.
        """

        if not auto_approve:
            return {
                "ok": False,
                "refused": True,
                "message": "terraform apply changes real infrastructure. Re-run "
                "with auto_approve=True to proceed (preview first with "
                "arvan_iac_terraform_plan).",
            }
        with _workspace(files, directory) as workdir:
            steps: dict[str, Any] = {}
            if init:
                steps["init"] = await run_command(
                    ["terraform", "init", "-input=false", "-no-color"],
                    cwd=workdir, timeout=timeout, env_extra=_tf_env(),
                )
            steps["apply"] = await run_command(
                ["terraform", "apply", "-auto-approve", "-input=false", "-no-color"],
                cwd=workdir, timeout=max(timeout, 600.0), env_extra=_tf_env(),
            )
            steps["ok"] = steps["apply"].get("ok", False)
            return steps

    @mcp.tool()
    async def arvan_iac_terraform_destroy(
        files: dict[str, str] | None = None,
        directory: str | None = None,
        auto_approve: bool = False,
    ) -> Any:
        """Run ``terraform destroy`` (tears down infrastructure; needs auto_approve)."""

        if not auto_approve:
            return {
                "ok": False,
                "refused": True,
                "message": "terraform destroy deletes real infrastructure. Re-run "
                "with auto_approve=True to proceed.",
            }
        with _workspace(files, directory) as workdir:
            return await run_command(
                ["terraform", "destroy", "-auto-approve", "-input=false", "-no-color"],
                cwd=workdir, timeout=max(timeout, 600.0), env_extra=_tf_env(),
            )

    @mcp.tool()
    async def arvan_iac_tflint(
        files: dict[str, str] | None = None, directory: str | None = None
    ) -> Any:
        """Lint Terraform with tflint (best-practice and provider checks)."""

        with _workspace(files, directory) as workdir:
            return await run_command(
                ["tflint", "--no-color", "--format", "json", "--chdir", workdir],
                cwd=workdir,
                timeout=timeout,
            )

    @mcp.tool()
    async def arvan_iac_checkov(
        files: dict[str, str] | None = None,
        directory: str | None = None,
        framework: str | None = None,
    ) -> Any:
        """Scan IaC for misconfigurations & security issues with Checkov.

        ``framework`` optionally narrows the scan (e.g. ``terraform``,
        ``kubernetes``, ``dockerfile``).
        """

        with _workspace(files, directory) as workdir:
            cmd = ["checkov", "-d", workdir, "-o", "json", "--compact", "--quiet"]
            if framework:
                cmd += ["--framework", framework]
            return _maybe_json(await run_command(cmd, cwd=workdir, timeout=timeout))

    @mcp.tool()
    async def arvan_iac_validate_kubernetes(
        manifest: str | None = None,
        files: dict[str, str] | None = None,
        directory: str | None = None,
    ) -> Any:
        """Validate Kubernetes manifests against the schema with kubeconform.

        Pass a single ``manifest`` YAML string, or ``files``/``directory``.
        """

        if manifest is not None and not files and not directory:
            files = {"manifest.yaml": manifest}
        with _workspace(files, directory) as workdir:
            return _maybe_json(
                await run_command(
                    ["kubeconform", "-summary", "-output", "json", workdir],
                    cwd=workdir,
                    timeout=timeout,
                )
            )

    @mcp.tool()
    async def arvan_iac_kube_linter(
        manifest: str | None = None,
        files: dict[str, str] | None = None,
        directory: str | None = None,
    ) -> Any:
        """Lint Kubernetes manifests for security/correctness with kube-linter."""

        if manifest is not None and not files and not directory:
            files = {"manifest.yaml": manifest}
        with _workspace(files, directory) as workdir:
            return await run_command(
                ["kube-linter", "lint", workdir, "--format", "json"],
                cwd=workdir,
                timeout=timeout,
            )

    @mcp.tool()
    async def arvan_iac_lint_dockerfile(content: str) -> Any:
        """Lint a Dockerfile with hadolint (reads the content from stdin)."""

        return _maybe_json(
            await run_command(
                ["hadolint", "--format", "json", "-"],
                input_text=content,
                timeout=timeout,
            )
        )

    @mcp.tool()
    async def arvan_iac_lint_yaml(content: str) -> Any:
        """Lint a YAML document with yamllint (reads the content from stdin)."""

        return await run_command(
            ["yamllint", "-f", "parsable", "-"], input_text=content, timeout=timeout
        )

    @mcp.tool()
    async def arvan_iac_trivy_config(
        files: dict[str, str] | None = None, directory: str | None = None
    ) -> Any:
        """Scan IaC/config for security issues with Trivy (``trivy config``)."""

        with _workspace(files, directory) as workdir:
            return _maybe_json(
                await run_command(
                    ["trivy", "config", "--format", "json", "--quiet", workdir],
                    cwd=workdir,
                    timeout=timeout,
                )
            )

    @mcp.tool()
    async def arvan_iac_terraform_cost(
        files: dict[str, str] | None = None, directory: str | None = None
    ) -> Any:
        """Estimate Terraform cost with Infracost (``infracost breakdown``)."""

        with _workspace(files, directory) as workdir:
            return _maybe_json(
                await run_command(
                    ["infracost", "breakdown", "--path", workdir, "--format", "json"],
                    cwd=workdir,
                    timeout=timeout,
                )
            )

    @mcp.tool()
    async def arvan_iac_packer_validate(
        files: dict[str, str] | None = None, directory: str | None = None
    ) -> Any:
        """Validate a Packer template (``packer validate``)."""

        with _workspace(files, directory) as workdir:
            return await run_command(
                ["packer", "validate", workdir], cwd=workdir, timeout=timeout
            )

    @mcp.tool()
    async def arvan_iac_opentofu_validate(
        files: dict[str, str] | None = None,
        directory: str | None = None,
        init: bool = True,
    ) -> Any:
        """Validate OpenTofu configuration (``tofu validate``)."""

        with _workspace(files, directory) as workdir:
            steps: dict[str, Any] = {}
            if init:
                steps["init"] = await run_command(
                    ["tofu", "init", "-backend=false", "-input=false", "-no-color"],
                    cwd=workdir, timeout=timeout,
                )
            steps["validate"] = _maybe_json(
                await run_command(
                    ["tofu", "validate", "-no-color", "-json"],
                    cwd=workdir, timeout=timeout,
                )
            )
            steps["ok"] = steps["validate"].get("ok", False)
            return steps

    @mcp.tool()
    async def arvan_iac_tfsec(
        files: dict[str, str] | None = None, directory: str | None = None
    ) -> Any:
        """Scan Terraform for security issues with tfsec."""

        with _workspace(files, directory) as workdir:
            return _maybe_json(
                await run_command(
                    ["tfsec", workdir, "--format", "json", "--no-color"],
                    cwd=workdir, timeout=timeout,
                )
            )
