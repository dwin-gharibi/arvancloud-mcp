from __future__ import annotations

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _structured(result):
    if result.structuredContent:
        data = result.structuredContent
        return data.get("result", data)
    for block in result.content:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except ValueError:
                return text
    return None


async def main() -> int:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "arvancloud_mcp"],
        env={**os.environ, "ARVAN_TRANSPORT": "stdio"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = (await session.list_tools()).tools
            print(f"tools exposed: {len(tools)}")

            caps = _structured(await session.call_tool("arvan_capabilities", {}))
            print("services:", ", ".join(sorted((caps or {}).get("services", {}))))

            doctor = _structured(await session.call_tool("arvan_doctor", {}))
            api = (doctor or {}).get("api", {})
            print(f"api configured: {api.get('configured')} ok: {api.get('ok')}")
            installed = [k for k, v in (doctor or {}).get("tools", {}).items() if v]
            print("CLI tools installed:", ", ".join(installed) or "(none)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
