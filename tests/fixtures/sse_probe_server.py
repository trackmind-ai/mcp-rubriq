# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: GPL-3.0-or-later

"""
tests/fixtures/sse_probe_server.py

A minimal SSE-transport MCP server, for exercising MCP-Rubriq's --transport sse
path end-to-end against a real (if local) network server. SSE is legacy
relative to streamable HTTP (see http_probe_server.py) but still in the wild.

Port is configurable via the MCP_RUBRIQ_FIXTURE_PORT env var (default 8933).

Run directly: python tests/fixtures/sse_probe_server.py
Then, e.g.:   python scripts/lint.py --transport sse --url http://127.0.0.1:8933/sse
"""

import os

from mcp.server.fastmcp import FastMCP

_PORT = int(os.environ.get("MCP_RUBRIQ_FIXTURE_PORT", "8933"))

mcp = FastMCP("mcp-rubriq-sse-probe", port=_PORT)


@mcp.tool()
def echo(text: str) -> str:
    """Echo back the given text."""
    return text


if __name__ == "__main__":
    mcp.run(transport="sse")
