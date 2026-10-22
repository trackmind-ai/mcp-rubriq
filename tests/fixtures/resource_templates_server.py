# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: GPL-3.0-or-later

"""
tests/fixtures/resource_templates_server.py

A stdio MCP server that exposes both static resources AND resource
templates (`resources/templates/list`). MCP-Rubriq's `_introspect_session`
currently never calls `list_resource_templates()`, so a server like this one
has its templates silently dropped rather than surfaced or flagged.

Run directly: python tests/fixtures/resource_templates_server.py
"""

import asyncio

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from pydantic import (
    # mcp.types re-exports AnyUrl unofficially (no __all__ entry) — import from the real source
    AnyUrl,
)

app = Server("mcp-rubriq-resource-templates")


@app.list_resources()
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri=AnyUrl("file:///workspace/README.md"),
            name="readme",
            description="The workspace README.",
            mimeType="text/markdown",
        )
    ]


@app.list_resource_templates()
async def list_resource_templates() -> list[types.ResourceTemplate]:
    return [
        types.ResourceTemplate(
            name="project-file",
            uriTemplate="file:///workspace/{path}",
            description="Any file within the workspace, addressed by relative path.",
            mimeType=None,
        ),
        types.ResourceTemplate(
            name="git-commit",
            uriTemplate="git://commit/{sha}",
            description="A specific commit by SHA in the current repository.",
            mimeType=None,
        ),
    ]


@app.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    return f"[stub] contents of {uri}"


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
