# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/fixtures/god_tool_wrong_fix_server.py

A001<->A002 conflict resolution fixture. Demonstrates the WRONG way
to fix tool bloat: instead of large_surface_server.py's 22 granular tools,
this server "consolidates" them into a single mega-tool with an action/mode
switch and 9 parameters. This trips A001's fix criteria (tool_count is low)
but should trip A002 (God-Tool Pattern) instead — the exact trap the A001<->
A002 resolution note in both rule files describes.

Pairs with consolidated_correct_fix_server.py, which consolidates the SAME
conceptual surface the right way (by outcome/intent, no action switch).

Run directly: python tests/fixtures/god_tool_wrong_fix_server.py
"""

import asyncio

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("mcp-rubriq-god-tool-wrong-fix")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="manage_tasks",
            description=(
                "Manages tasks: create, update, close, archive, assign, comment, "
                "search, or export, depending on the action parameter."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Which operation to perform.",
                        "enum": [
                            "create",
                            "update",
                            "close",
                            "archive",
                            "assign",
                            "comment",
                            "search",
                            "export",
                        ],
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Task identifier (for non-create actions).",
                    },
                    "title": {"type": "string", "description": "Task title (for create/update)."},
                    "description": {
                        "type": "string",
                        "description": "Task description (for create/update).",
                    },
                    "assignee": {
                        "type": "string",
                        "description": "User to assign (for assign action).",
                    },
                    "comment_text": {
                        "type": "string",
                        "description": "Comment body (for comment action).",
                    },
                    "query": {"type": "string", "description": "Search query (for search action)."},
                    "export_format": {
                        "type": "string",
                        "description": "Output format (for export action).",
                    },
                    "archive_reason": {
                        "type": "string",
                        "description": "Reason (for archive action).",
                    },
                },
                "required": ["action"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    return [
        types.TextContent(
            type="text", text=f"[stub] called {name} with action={arguments.get('action')}"
        )
    ]


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
