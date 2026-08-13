# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/fixtures/omnibus_params_server.py

S007 (Omnibus/Blob Parameter) fixture: a tool with an unconstrained
catch-all object parameter (additionalProperties: true, no defined shape),
alongside a clean control tool whose object parameter DOES define its own
shape, and a third tool whose blob param is explicitly documented as
intentional (arbitrary user tags) — testing the judge's contextual
distinction between "undocumented blob" and "documented arbitrary data."

Run directly: python tests/fixtures/omnibus_params_server.py
"""

import asyncio

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("mcp-rubriq-omnibus-params")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        # THE VIOLATION: config accepts literally anything, undocumented.
        types.Tool(
            name="configure_pipeline",
            description="Configures the data pipeline with the given settings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pipeline_id": {"type": "string", "description": "Pipeline to configure."},
                    "config": {
                        "type": "object",
                        "description": "Configuration settings.",
                        "additionalProperties": True,
                    },
                },
                "required": ["pipeline_id", "config"],
            },
        ),
        # CONTROL: object property with its own defined shape — must NOT flag.
        types.Tool(
            name="create_address",
            description="Creates a shipping address record.",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {
                        "type": "object",
                        "description": "The shipping address.",
                        "properties": {
                            "street": {"type": "string"},
                            "city": {"type": "string"},
                            "postal_code": {"type": "string"},
                        },
                    },
                },
                "required": ["address"],
            },
        ),
        # BORDERLINE: blob param, but explicitly documented as intentionally
        # arbitrary — should not be flagged the same way as the undocumented
        # violation above.
        types.Tool(
            name="tag_resource",
            description="Tags a resource with arbitrary user-defined key-value metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string", "description": "Resource to tag."},
                    "tags": {
                        "type": "object",
                        "description": (
                            "Arbitrary user-defined tags as free-form key-value pairs; "
                            "no fixed schema is expected."
                        ),
                        "additionalProperties": True,
                    },
                },
                "required": ["resource_id", "tags"],
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
