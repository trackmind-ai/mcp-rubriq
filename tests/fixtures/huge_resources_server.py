# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: GPL-3.0-or-later

"""
tests/fixtures/huge_resources_server.py

A stdio MCP server exposing 300 static resources with realistic descriptions.

Purpose: the pipeline forwards the FULL resources list verbatim into the
AnnotatedServerModel — this fixture measures what that does to the judge's
input size on a resource-heavy server (a real filesystem server over a big
tree behaves like this). The matrix case records output size; if it's
unreasonable, the finding drives a truncation/summarization decision.

Run directly: python tests/fixtures/huge_resources_server.py
"""

import asyncio

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from pydantic import (
    # mcp.types re-exports AnyUrl unofficially (no __all__ entry) — import from the real source
    AnyUrl,
)

app = Server("mcp-rubriq-huge-resources")

_CATEGORIES = ["reports", "invoices", "contracts", "designs", "exports", "logs"]


@app.list_resources()
async def list_resources() -> list[types.Resource]:
    resources = []
    for cat in _CATEGORIES:
        for i in range(50):  # 6 × 50 = 300
            resources.append(
                types.Resource(
                    uri=AnyUrl(f"app://{cat}/{i:04d}"),
                    name=f"{cat}-{i:04d}",
                    description=(
                        f"Document {i:04d} in the {cat} collection, retained under the "
                        f"standard archival policy and addressable for read-only access."
                    ),
                    mimeType="application/pdf",
                )
            )
    return resources


@app.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    return f"[stub] contents of {uri}"


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
