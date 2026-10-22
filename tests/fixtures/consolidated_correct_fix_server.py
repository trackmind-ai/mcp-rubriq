# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: GPL-3.0-or-later

"""
tests/fixtures/consolidated_correct_fix_server.py

A001<->A002 conflict resolution fixture. Demonstrates the RIGHT way
to fix tool bloat: consolidating large_surface_server.py's 22 granular tools
(list_projects, create_task, update_task, close_task, archive_task,
assign_task, comment_on_task, search_tasks, export_report, ...) down to 6
intent-specific tools, each doing one clear thing — NOT via an action/mode
switch (see god_tool_wrong_fix_server.py for the wrong way).

Should pass BOTH A001 (few tools, no bloat) and A002 (no tool has an action
parameter or an excessive parameter count).

Run directly: python tests/fixtures/consolidated_correct_fix_server.py
"""

import asyncio

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("mcp-rubriq-consolidated-correct-fix")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        # create+update collapse into one natural intent: "save this task as
        # given" — not an arbitrary mode switch, just upsert semantics.
        types.Tool(
            name="upsert_task",
            description=(
                "Creates a new task, or updates an existing one if task_id is "
                "provided. Returns the resulting task record."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Existing task id to update; omit to create a new task.",
                    },
                    "title": {"type": "string", "description": "Task title."},
                    "description": {"type": "string", "description": "Task description."},
                },
                "required": ["title"],
            },
        ),
        types.Tool(
            name="search_tasks",
            description=(
                "Searches tasks by free-text query, replacing the old list/search split "
                "with one flexible interface."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Free-text search query."},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="archive_task",
            description=(
                "Archives a task, removing it from active views without deleting its history."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task to archive."},
                    "reason": {"type": "string", "description": "Optional reason for archiving."},
                },
                "required": ["task_id"],
            },
        ),
        types.Tool(
            name="assign_task",
            description="Assigns a task to a user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task to assign."},
                    "assignee": {"type": "string", "description": "User to assign the task to."},
                },
                "required": ["task_id", "assignee"],
            },
        ),
        types.Tool(
            name="comment_on_task",
            description="Adds a comment to a task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task to comment on."},
                    "text": {"type": "string", "description": "Comment body."},
                },
                "required": ["task_id", "text"],
            },
        ),
        types.Tool(
            name="export_report",
            description="Exports a summary report of all tasks in the requested format.",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": "Output format, e.g. 'csv' or 'pdf'.",
                        "enum": ["csv", "pdf"],
                    },
                },
                "required": ["format"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=f"[stub] called {name}")]


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
