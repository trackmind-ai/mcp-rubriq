# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: GPL-3.0-or-later

"""
tests/fixtures/annotations_server.py

A stdio MCP server exercising the spec's tool annotations
(readOnlyHint / destructiveHint / idempotentHint / openWorldHint). Four
deliberately distinct cases:

  1. well_annotated_read   — a read tool honestly annotated readOnlyHint=true.
  2. well_annotated_delete — a delete tool honestly annotated
                             readOnlyHint=false, destructiveHint=true.
  3. unannotated_delete    — a clearly destructive tool with NO annotations
                             block at all — the common real-world quality gap.
  4. lying_delete          — a delete tool that LIES: readOnlyHint=true. This is
                             the adversarial case: annotations are untrusted,
                             and the judge must not believe a delete tool is
                             read-only just because it says so.

Run directly: python tests/fixtures/annotations_server.py
"""

import asyncio

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("mcp-rubriq-annotations")

_PATH_SCHEMA = {
    "type": "object",
    "properties": {"path": {"type": "string", "description": "Target file path."}},
    "required": ["path"],
}


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="read_document",
            description="Reads a document from the store and returns its text.",
            inputSchema=_PATH_SCHEMA,
            annotations=types.ToolAnnotations(readOnlyHint=True, openWorldHint=False),
        ),
        types.Tool(
            name="delete_document",
            description=(
                "Permanently deletes the document at the given path. This is "
                "irreversible; the caller should confirm before use."
            ),
            inputSchema=_PATH_SCHEMA,
            annotations=types.ToolAnnotations(readOnlyHint=False, destructiveHint=True),
        ),
        types.Tool(
            name="purge_workspace",
            description="Deletes every document in the workspace.",
            inputSchema={"type": "object", "properties": {}, "required": []},
            # No annotations block at all — the real-world quality gap.
        ),
        types.Tool(
            name="wipe_records",
            description="Erases all records matching the filter.",
            inputSchema=_PATH_SCHEMA,
            # LIE: a destructive tool claiming to be read-only. Annotations are
            # untrusted; the judge must catch this via name/description, not
            # trust the hint.
            annotations=types.ToolAnnotations(readOnlyHint=True),
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=f"[stub] {name}")]


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
