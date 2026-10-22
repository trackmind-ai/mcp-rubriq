# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: GPL-3.0-or-later

"""
tests/fixtures/template_only_server.py

A stdio MCP server that exposes ONLY resource templates — no static
resources, no tools, no prompts. Distinct from resource_templates_server.py
(which mixes static + templated): this is the pure case the checklist calls
"resource-template-only servers".

Probes:
  - has_resources must be True from templates alone
  - template content (names, URI templates, descriptions) must
    reach the judge — including one deliberately LOW-QUALITY template
    (no description, ambiguous single-letter variable) as R-series bait.

Run directly: python tests/fixtures/template_only_server.py
"""

import asyncio

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from pydantic import (
    # mcp.types re-exports AnyUrl unofficially (no __all__ entry) — import from the real source
    AnyUrl,
)

app = Server("mcp-rubriq-template-only")


@app.list_resource_templates()
async def list_resource_templates() -> list[types.ResourceTemplate]:
    return [
        # A well-formed template: named, described, unambiguous variable.
        types.ResourceTemplate(
            name="user-profile",
            uriTemplate="app://users/{user_id}/profile",
            description="The profile document for a user, addressed by their unique user id.",
            mimeType="application/json",
        ),
        # A deliberately poor template: no description, ambiguous variable
        # name — exactly what a future R-series quality rule should flag.
        types.ResourceTemplate(
            name="thing",
            uriTemplate="app://data/{x}",
            description=None,
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
