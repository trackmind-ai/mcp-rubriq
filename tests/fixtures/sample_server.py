# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/fixtures/sample_server.py

A minimal in-process MCP server for testing the introspection client.
It exposes a small set of tools, resources, and prompts via stdio.
"""

import asyncio

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from pydantic import (
    # mcp.types re-exports AnyUrl unofficially (no __all__ entry) — import from the real source
    AnyUrl,
)

app = Server("mcp-rubriq-test-server")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="read_file",
            description=(
                "Reads the contents of a file at the given path and returns it as a string."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to the file to read."}
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="delete_file",
            description="",  # intentionally empty — quality issue for later linting tests
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"}  # no description on property
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="list_directory",
            description="Lists the contents of a directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the directory to list."},
                    "recursive": {"type": "boolean", "description": "Whether to list recursively."},
                },
                "required": ["path"],
            },
        ),
    ]


@app.list_resources()
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri=AnyUrl("file:///workspace"),
            name="workspace",
            description="The root workspace directory.",
            mimeType=None,
        )
    ]


@app.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="summarize",
            description="Summarize the provided text into a concise paragraph.",
            arguments=[
                types.PromptArgument(
                    name="text",
                    description="The text to summarize.",
                    required=True,
                )
            ],
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=f"[stub] called {name} with {arguments}")]


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
