from __future__ import annotations

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> int:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "arvancloud_mcp"],
        env={**os.environ, "ARVAN_TRANSPORT": "stdio"},
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"✓ connected to: {init.serverInfo.name} {init.serverInfo.version}")

            tools = (await session.list_tools()).tools
            names = sorted(t.name for t in tools)
            print(f"✓ {len(names)} tools advertised")

            required = {
                "arvan_request",
                "arvan_capabilities",
                "arvan_list_servers",
                "arvan_wait_for_server",
                "arvan_create_ssh_key",
                "arvan_create_a_record",
                "arvan_vod_list_channels",
                "arvan_live_list_channels",
                "arvan_s3_list_buckets",
                "arvan_s3_put_object",
                "arvan_ssh_run",
                "arvan_ssh_run_script",
            }
            missing = required - set(names)
            assert not missing, f"missing tools: {missing}"
            print("✓ key tools present:", ", ".join(sorted(required)))

            resources = (await session.list_resources()).resources
            res_uris = {str(r.uri) for r in resources}
            assert "arvan://capabilities" in res_uris, res_uris
            print("✓ capabilities resource present")

            result = await session.call_tool("arvan_capabilities", {})
            assert not result.isError, result
            data = result.structuredContent or {}
            svc = data.get("services", {})
            print(f"✓ arvan_capabilities returned {len(svc)} services: "
                  f"{', '.join(sorted(svc))}")

            detail = await session.call_tool("arvan_capabilities", {"service": "dns"})
            assert not detail.isError, detail
            eps = (detail.structuredContent or {}).get("endpoints", [])
            print(f"✓ dns service exposes {len(eps)} endpoints")

    print("\nALL SMOKE CHECKS PASSED ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
