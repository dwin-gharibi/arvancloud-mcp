"""ArvanCloud MCP server.

A Model Context Protocol server that exposes the ArvanCloud platform
(https://www.arvancloud.ir) — Cloud Server / IaaS, CDN, Cloud DNS,
Video on Demand and more — to MCP-compatible clients such as Claude.

The server talks to the unified ArvanCloud API ("napi",
https://napi.arvancloud.ir) and provides both ergonomic, typed tools for
the most common operations and a generic escape-hatch tool that can reach
*any* endpoint the platform exposes.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
