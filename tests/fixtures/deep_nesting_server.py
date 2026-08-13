# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/fixtures/deep_nesting_server.py

A stdio MCP server whose tool schemas push _resolve_schema past its comfort
zone — beyond the shapes schema_edge_cases_server.py already covers:
  - a $ref chain deeper than the depth-10 guard (must degrade, not crash)
  - a genuinely CYCLIC $ref pair (must terminate)
  - oneOf → $ref → allOf composition in one schema
  - an array property whose `items` is a $ref (items aren't resolved today —
    documents the boundary rather than asserting resolution)

Run directly: python tests/fixtures/deep_nesting_server.py
"""

import asyncio
from typing import Any

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("mcp-rubriq-deep-nesting")


def _deep_chain_defs(depth: int) -> dict:
    """L0 → L1 → ... → L<depth>, with real properties only at the end."""
    defs: dict[str, Any] = {f"L{i}": {"$ref": f"#/$defs/L{i + 1}"} for i in range(depth)}
    defs[f"L{depth}"] = {
        "type": "object",
        "properties": {"leaf": {"type": "string", "description": "The value at the bottom."}},
        "required": ["leaf"],
    }
    return defs


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        # 1. 15-link chain: exceeds the resolver's depth-10 guard. The schema
        #    will read as unresolved/empty — acceptable degradation; the case
        #    exists to prove there's no crash, hang, or RecursionError.
        types.Tool(
            name="chase_deep_chain",
            description=(
                "Tool whose schema is a fifteen-level $ref chain, past the resolver depth guard."
            ),
            inputSchema={"$ref": "#/$defs/L0", "$defs": _deep_chain_defs(15)},
        ),
        # 2. Cyclic refs: A → B → A. A hostile-or-buggy generator can emit this.
        types.Tool(
            name="chase_cyclic_ref",
            description=(
                "Tool whose schema contains a deliberate $ref cycle between two definitions."
            ),
            inputSchema={
                "$ref": "#/$defs/A",
                "$defs": {"A": {"$ref": "#/$defs/B"}, "B": {"$ref": "#/$defs/A"}},
            },
        ),
        # 3. Combo: oneOf whose branches are a $ref-to-allOf and an inline object.
        types.Tool(
            name="combo_query",
            description="Query via a composed structured filter or a plain free-text string.",
            inputSchema={
                "oneOf": [
                    {"$ref": "#/$defs/Composite"},
                    {
                        "type": "object",
                        "properties": {"raw": {"type": "string", "description": "Raw query text."}},
                        "required": ["raw"],
                    },
                ],
                "$defs": {
                    "Composite": {
                        "allOf": [
                            {
                                "type": "object",
                                "properties": {
                                    "field": {
                                        "type": "string",
                                        "description": "Field to filter on.",
                                    }
                                },
                                "required": ["field"],
                            },
                            {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "string", "description": "Value to match."}
                                },
                                "required": ["value"],
                            },
                        ]
                    }
                },
            },
        ),
        # 4. Array property with $ref items — resolvable type at the property
        #    level ("array"), unresolved one level down. Documents the boundary.
        types.Tool(
            name="batch_update",
            description=(
                "Applies a list of patch operations to the named record in one atomic batch."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "record_id": {"type": "string", "description": "Record to patch."},
                    "patches": {
                        "type": "array",
                        "description": "Patch operations to apply, in order.",
                        "items": {"$ref": "#/$defs/Patch"},
                    },
                },
                "required": ["record_id", "patches"],
                "$defs": {
                    "Patch": {
                        "type": "object",
                        "properties": {
                            "op": {"type": "string", "enum": ["add", "remove", "replace"]},
                            "path": {"type": "string"},
                        },
                    }
                },
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
