# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
conftest.py — Shared pytest fixtures for MCP-Rubriq tests.

The linter's code lives inside the plugin payload at
plugins/mcp-rubriq/skills/mcp-rubriq/ (models/, rulebook/, introspection/,
scripts/). Tests live outside the payload, at the repo root, so the shipped
skill stays lean. This conftest puts the skill directory on sys.path once, so
every test file can import `models.*`, `rulebook.*`, and `introspection.*`
exactly the way the skill's own code does.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SKILL_DIR = REPO_ROOT / "plugins" / "mcp-rubriq" / "skills" / "mcp-rubriq"
sys.path.insert(0, str(SKILL_DIR))

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_tools_list():
    """A minimal MCP tools/list response with one good and one bad tool."""
    return {
        "tools": [
            {
                "name": "read_file",
                "description": (
                    "Reads the contents of a file at the given path and returns it as a string."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Absolute path to the file to read.",
                        }
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "delete_file",
                "description": "",  # intentionally empty — quality issue
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}  # no description on property
                    },
                    "required": ["path"],
                },
            },
        ]
    }


@pytest.fixture
def sample_resources_list():
    """A minimal MCP resources/list response."""
    return {
        "resources": [
            {
                "uri": "file:///workspace",
                "name": "workspace",
                "description": "The root workspace directory.",
                "mimeType": None,
            }
        ]
    }


@pytest.fixture
def sample_prompts_list():
    """A minimal MCP prompts/list response."""
    return {
        "prompts": [
            {
                "name": "summarize",
                "description": "Summarize the provided text into a concise paragraph.",
                "arguments": [
                    {"name": "text", "description": "The text to summarize.", "required": True}
                ],
            }
        ]
    }


@pytest.fixture
def sample_server_info():
    """A minimal MCP server initialization response."""
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": {"name": "test-mcp-server", "version": "0.1.0"},
        "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
    }
