# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/fixtures/prompt_edge_cases_server.py

A stdio MCP server exercising prompt-argument edge cases — the prompt-side
mirror of schema_edge_cases_server.py:
  - a prompt with no description at all
  - a prompt with many arguments, several missing descriptions
  - a required argument with no description (worst case for a caller)
  - a prompt with zero arguments (legitimate)
  - a prompt whose name breaks the usual charset conventions

Probes prompt-content forwarding (prompt content must reach the judge,
arguments included) and gives the R-series prompt-quality rules concrete bait.

Run directly: python tests/fixtures/prompt_edge_cases_server.py
"""

import asyncio

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("mcp-rubriq-prompt-edge-cases")


@app.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    return [
        # 1. No description at all.
        types.Prompt(name="mystery_prompt", description=None, arguments=[]),
        # 2. Many arguments, mixed description quality.
        types.Prompt(
            name="generate_report",
            description="Generates a formatted report over the requested date range.",
            arguments=[
                types.PromptArgument(
                    name="start_date", description="Range start, ISO-8601 date.", required=True
                ),
                types.PromptArgument(
                    name="end_date", description=None, required=True
                ),  # required, undescribed
                types.PromptArgument(
                    name="fmt", description=None, required=False
                ),  # ambiguous AND undescribed
                types.PromptArgument(
                    name="include_charts", description="Whether to embed charts.", required=False
                ),
                types.PromptArgument(name="tz", description=None, required=False),
                types.PromptArgument(
                    name="locale",
                    description="BCP-47 locale for number formatting.",
                    required=False,
                ),
                types.PromptArgument(name="depth", description=None, required=False),
                types.PromptArgument(
                    name="x", description=None, required=False
                ),  # single-letter name
            ],
        ),
        # 3. Zero arguments — perfectly legitimate, must not be penalized.
        types.Prompt(
            name="daily_standup",
            description="Produces the daily standup summary from today's activity.",
            arguments=[],
        ),
        # 4. Name with a space — breaks the usual identifier conventions.
        types.Prompt(
            name="weird prompt name",
            description=(
                "A prompt whose name contains a space, testing name-charset handling for prompts."
            ),
            arguments=[],
        ),
    ]


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
