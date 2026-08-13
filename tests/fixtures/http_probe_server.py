# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/fixtures/http_probe_server.py

A minimal streamable-HTTP MCP server, for exercising MCP-Rubriq's --transport
http path end-to-end against a real (if local) network server rather than
just stdio pipes.

Port is configurable via the MCP_RUBRIQ_FIXTURE_PORT env var (default 8931) so
a test runner can avoid clashes with anything else already listening.

Run directly: python tests/fixtures/http_probe_server.py
Then, e.g.:   python scripts/lint.py --transport http --url http://127.0.0.1:8931/mcp
"""

import os

from mcp.server.fastmcp import FastMCP

_PORT = int(os.environ.get("MCP_RUBRIQ_FIXTURE_PORT", "8931"))

mcp = FastMCP("mcp-rubriq-http-probe", port=_PORT)


@mcp.tool()
def echo(text: str) -> str:
    """Echo back the given text."""
    return text


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers and return the sum."""
    return a + b


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
