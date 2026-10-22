# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: GPL-3.0-or-later

"""
tests/fixtures/unicode_server.py

A stdio MCP server with non-ASCII tool names, descriptions, resource and
prompt metadata. Probes:
  - end-to-end UTF-8 survival (stdio pipes on Windows are a classic mojibake
    source — cp1252 vs utf-8)
  - T005: non-ASCII names should flag name_invalid_chars (the MCP spec and
    every real client expect [a-zA-Z0-9_-.] names)
  - the annotator must not crash on emoji/CJK/RTL text anywhere

Run directly: python tests/fixtures/unicode_server.py
"""

import asyncio

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from pydantic import (
    # mcp.types re-exports AnyUrl unofficially (no __all__ entry) — import from the real source
    AnyUrl,
)

app = Server("mcp-rubriq-unicode-テスト")  # server name itself is non-ASCII


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        # Non-ASCII name (accented latin) — should flag name_invalid_chars.
        types.Tool(
            name="café_search",
            description="Searches the café menu for matching items by name or ingredient.",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search text."}},
                "required": ["query"],
            },
        ),
        # CJK name — should flag name_invalid_chars.
        types.Tool(
            name="取得資料",
            description="データストアからレコードを取得します。",
            inputSchema={
                "type": "object",
                "properties": {"id": {"type": "string", "description": "レコードID"}},
                "required": ["id"],
            },
        ),
        # Emoji in name — should flag name_invalid_chars.
        types.Tool(
            name="deploy_\U0001f680",
            description=(
                "Deploys the application to the selected environment with a progress emoji."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "env": {"type": "string", "description": "Target environment name."}
                },
                "required": ["env"],
            },
        ),
        # Valid ASCII name, non-ASCII (Arabic, RTL) description — name must NOT flag.
        types.Tool(
            name="translate_text",
            description=(
                "يترجم النص المقدم إلى اللغة المستهدفة. Translates the provided text "
                "into the target language."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to translate."},
                    "target": {"type": "string", "description": "BCP-47 target language code."},
                },
                "required": ["text", "target"],
            },
        ),
    ]


@app.list_resources()
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri=AnyUrl("file:///docs/ガイド.md"),
            name="ユーザーガイド",
            description="日本語のユーザーガイド。",
            mimeType="text/markdown",
        )
    ]


@app.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="résumé_review",
            description="Reviews a résumé — with “smart quotes”, em–dashes, and ümläuts.",
            arguments=[
                types.PromptArgument(name="text", description="Résumé text.", required=True)
            ],
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=f"[stub] called {name}")]


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
