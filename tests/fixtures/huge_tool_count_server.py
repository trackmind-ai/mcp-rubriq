# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/fixtures/huge_tool_count_server.py

A stdio MCP server exposing 120 well-formed tools — an order of magnitude past
the tool_count_high threshold (20). Probes:
  - scale: does introspection/annotation handle 100+ tools without choking?
  - A001 at extreme scale (the flag should fire; nothing else should)
  - output size: how large does the AnnotatedServerModel get?

Every tool is individually clean (good name, real description, typed schema)
so any *other* flag firing here is a false positive.

Run directly: python tests/fixtures/huge_tool_count_server.py
"""

import asyncio

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("mcp-rubriq-huge-tool-count")

# 120 distinct snake_case names built from verb+noun pairs — no near-duplicate
# pairs by construction (every verb/noun combination differs by whole words).
_VERBS = [
    "create",
    "fetch",
    "archive",
    "publish",
    "validate",
    "transform",
    "schedule",
    "cancel",
    "approve",
    "reject",
    "merge",
    "export",
]
_NOUNS = [
    "invoice",
    "customer",
    "shipment",
    "warehouse",
    "campaign",
    "subscription",
    "webhook",
    "dashboard",
    "territory",
    "forecast",
]


def _make_tool(verb: str, noun: str) -> types.Tool:
    name = f"{verb}_{noun}"
    return types.Tool(
        name=name,
        description=(
            f"{verb.capitalize()}s the specified {noun} record in the system of record, "
            f"validating permissions and returning the updated {noun} state."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                f"{noun}_id": {
                    "type": "string",
                    "description": f"Unique identifier of the {noun} to {verb}.",
                }
            },
            "required": [f"{noun}_id"],
        },
    )


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [_make_tool(v, n) for v in _VERBS for n in _NOUNS]  # 12 × 10 = 120


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=f"[stub] called {name}")]


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
