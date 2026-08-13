# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/fixtures/slow_start_server.py

A stdio MCP server that sleeps before completing its handshake, simulating
a cold `npx` install (package download) on first run. Used to verify that
--timeout is respected and that a timeout produces MCP-Rubriq's actionable
error message rather than a raw traceback.

Delay is configurable via the MCP_RUBRIQ_FIXTURE_DELAY env var (seconds,
default 5) so a test runner can pick a delay relative to the --timeout
it's probing with.

Run directly: python tests/fixtures/slow_start_server.py
"""

import asyncio
import os

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("mcp-rubriq-slow-start")

_DELAY_SECONDS = float(os.environ.get("MCP_RUBRIQ_FIXTURE_DELAY", "5"))


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="ping",
            description="Trivial tool, present only so the server has something to list.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    return [types.TextContent(type="text", text="pong")]


async def main():
    await asyncio.sleep(_DELAY_SECONDS)
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
