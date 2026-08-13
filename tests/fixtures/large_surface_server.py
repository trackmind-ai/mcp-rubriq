# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/fixtures/large_surface_server.py

A stdio MCP server with a deliberately large, messy tool surface to exercise
server-level Annotator checks that a small fixture can't reach:
  - tool_count_high (> 20 tools)                         -> A001 tool bloat
  - naming_inconsistent (mixed snake_case / camelCase)     -> T003
  - duplicate_name_pairs (near-duplicate names, edit dist <= 2) -> T006
  - ambiguous single-verb names                            -> T004

Run directly: python tests/fixtures/large_surface_server.py
"""

import asyncio

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("mcp-rubriq-large-surface")

# 12 distinct, unrelated snake_case tools (bulk of the count).
_GENERIC_TOOLS = [
    "list_projects",
    "create_task",
    "update_task",
    "close_task",
    "archive_task",
    "assign_task",
    "comment_on_task",
    "search_tasks",
    "export_report",
    "import_data",
    "sync_calendar",
    "notify_team",
]

# 5 sequentially-numbered tools — a very common real naming pattern. Each
# neighbor pair differs by one character ("get_item_1" vs "get_item_2"), so
# the Levenshtein-based near-duplicate check (threshold <= 2) flags EVERY
# pair, not just genuine typos. Demonstrates a false-positive-flood gap
# distinct from the intentional get_user/get_users pair below.
_SEQUENTIAL_TOOLS = [f"get_item_{i}" for i in range(5)]

# One genuine near-duplicate pair (edit distance 1) that T006 SHOULD catch.
_NEAR_DUPLICATE_PAIR = ["get_user", "get_users"]

# 3 camelCase tools, to force naming_inconsistent = True.
_CAMEL_CASE_TOOLS = [
    "fetchUserProfile",
    "updateUserProfile",
    "run",
]  # "run" also hits the ambiguous-name list

_SNAKE_CASE_TOOLS = _GENERIC_TOOLS + _SEQUENTIAL_TOOLS + _NEAR_DUPLICATE_PAIR


def _make_tool(name: str) -> types.Tool:
    return types.Tool(
        name=name,
        description=(
            f"Auto-generated fixture tool '{name}' for large-surface server-level annotation tests."
        ),
        inputSchema={
            "type": "object",
            "properties": {"id": {"type": "string", "description": "Identifier to operate on."}},
            "required": ["id"],
        },
    )


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [_make_tool(n) for n in _SNAKE_CASE_TOOLS + _CAMEL_CASE_TOOLS]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=f"[stub] called {name} with {arguments}")]


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
