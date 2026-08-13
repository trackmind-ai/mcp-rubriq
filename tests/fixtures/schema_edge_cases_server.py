# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/fixtures/schema_edge_cases_server.py

A stdio MCP server built to probe known Annotator/model gaps around
JSON Schema shapes that don't fit a flat {type, properties, required} object:
  - `$ref` + `$defs` (common output of Pydantic/Zod schema generators)
  - `allOf` composition
  - `oneOf` unions with no top-level `properties` at all
  - `outputSchema` (newer MCP servers declare structured output)

Each tool is genuinely well-specified — the point is that MCP-Rubriq's mapping
layer (`_map_tool` in introspection/introspect.py) currently only reads
top-level `properties`/`required`, so these will look empty/under-specified
to the Annotator (false S001 "empty schema") even though they aren't.

Run directly: python tests/fixtures/schema_edge_cases_server.py
"""

import asyncio

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("mcp-rubriq-schema-edge-cases")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        # 1. $ref + $defs: top-level schema has no "properties" key at all —
        #    everything is behind a $ref into $defs. Genuinely well-specified,
        #    but _map_tool's flat properties.get() sees nothing.
        types.Tool(
            name="search_docs",
            description="Search indexed documents using a structured filter object.",
            inputSchema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "$ref": "#/$defs/SearchParams",
                "$defs": {
                    "SearchParams": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Free-text search query."},
                            "filters": {"$ref": "#/$defs/Filters"},
                        },
                        "required": ["query"],
                    },
                    "Filters": {
                        "type": "object",
                        "properties": {
                            "author": {"type": "string"},
                            "before": {"type": "string", "format": "date"},
                        },
                    },
                },
            },
        ),
        # 2. allOf composition: base object extended via allOf, no flat properties.
        types.Tool(
            name="update_record",
            description=(
                "Update a record, composing a base identity shape with patch fields via allOf."
            ),
            inputSchema={
                "allOf": [
                    {"$ref": "#/$defs/RecordId"},
                    {"$ref": "#/$defs/PatchFields"},
                ],
                "$defs": {
                    "RecordId": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Record identifier."}
                        },
                        "required": ["id"],
                    },
                    "PatchFields": {
                        "type": "object",
                        "properties": {"status": {"type": "string", "enum": ["open", "closed"]}},
                    },
                },
            },
        ),
        # 3. oneOf union at top level: two mutually exclusive input shapes.
        types.Tool(
            name="advanced_query",
            description="Run a query either by raw text or by a structured expression tree.",
            inputSchema={
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                    {
                        "type": "object",
                        "properties": {"expression": {"type": "object"}},
                        "required": ["expression"],
                    },
                ]
            },
        ),
        # 4. outputSchema present: MCP servers can declare structured output.
        #    ToolModel has no output_schema field today, so this is silently dropped.
        types.Tool(
            name="count_items",
            description=(
                "Count items matching a simple filter and return a structured count object."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Category to filter by."},
                },
                "required": ["category"],
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Number of matching items."},
                    "category": {"type": "string"},
                },
                "required": ["count"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=f"[stub] called {name} with {arguments}")]


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
