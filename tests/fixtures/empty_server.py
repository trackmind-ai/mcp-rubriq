# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/fixtures/empty_server.py

A stdio MCP server that registers NO handlers at all — zero tools, zero
resources, zero prompts, and (because the low-level SDK derives advertised
capabilities from registered handlers) no capability groups either.

Probes the floor of the pipeline: introspection must succeed and produce a
valid, fully-empty AnnotatedServerModel; the annotator must not divide by
zero, index into empty lists, or invent flags.

Run directly: python tests/fixtures/empty_server.py
"""

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("mcp-rubriq-empty")


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
