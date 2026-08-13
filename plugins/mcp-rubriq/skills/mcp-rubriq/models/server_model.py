# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
models/server_model.py

Normalized internal data models for mcp-rubriq.

These models are SDK-independent. The introspection tool maps raw MCP SDK
objects into these structures. Everything downstream (rulebook, judge, reporter)
works exclusively with these models — never with raw SDK objects.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Leaf models
# ---------------------------------------------------------------------------


class ToolInputProperty(BaseModel):
    """A single property inside a tool's input schema."""

    type: str | None = None
    description: str | None = None
    enum: list[Any] | None = None
    # Preserve any extra schema fields we don't explicitly model
    extra: dict[str, Any] = Field(default_factory=dict)


class ToolInputSchema(BaseModel):
    """A JSON Schema object describing a tool's accepted inputs (or,
    reused as-is, its structured output — see ToolModel.output_schema).

    Built from a raw schema that has already been resolved (see
    introspection/introspect.py's _resolve_schema): $ref/$defs looked up,
    allOf branches merged, and oneOf/anyOf unions flattened into the union
    of their branches' properties. is_union is set when the source schema
    was a oneOf/anyOf — in that case `required` deliberately does NOT
    represent "all of these are required together" (the variants may
    require different subsets), just the top-level schema's own required
    list, if any.
    """

    type: str = "object"
    properties: dict[str, ToolInputProperty] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    is_union: bool = False
    # Preserve any extra schema fields
    extra: dict[str, Any] = Field(default_factory=dict)


class PromptArgument(BaseModel):
    """A single argument accepted by a prompt."""

    name: str
    description: str | None = None
    required: bool = False


# ---------------------------------------------------------------------------
# Top-level entity models
# ---------------------------------------------------------------------------


class ToolAnnotations(BaseModel):
    """The MCP spec's optional `ToolAnnotations` (shipped 2025-03-26, unchanged
    at protocol 2025-11-25) — behavioral HINTS a server declares about a tool.

    All fields are Optional and default to None here deliberately: the SDK
    leaves an undeclared hint unset rather than applying the spec's textual
    defaults (`destructiveHint`/`openWorldHint` default true, the others
    false). Preserving None lets a rule distinguish "author never declared
    this" (None) from "author explicitly set it" (True/False) — the former is
    the meaningful quality signal.

    These are UNTRUSTED: an untrusted server can lie (say readOnlyHint=true on
    a delete tool). A rule may use them as corroborating metadata, never as
    proof of behavior.
    """

    title: str | None = None
    read_only_hint: bool | None = None
    destructive_hint: bool | None = None
    idempotent_hint: bool | None = None
    open_world_hint: bool | None = None


class ToolModel(BaseModel):
    """Normalized representation of a single MCP tool."""

    name: str
    description: str | None = None
    input_schema: ToolInputSchema = Field(default_factory=ToolInputSchema)
    output_schema: ToolInputSchema | None = None
    # The MCP spec's tool annotations (behavioral hints). None when the server
    # declared no annotations block at all.
    tool_annotations: ToolAnnotations | None = None


class ResourceModel(BaseModel):
    """Normalized representation of a single MCP resource."""

    uri: str
    name: str | None = None
    description: str | None = None
    mime_type: str | None = None


class ResourceTemplateModel(BaseModel):
    """Normalized representation of a single MCP resource template
    (a parameterized resource URI, e.g. 'file:///workspace/{path}')."""

    uri_template: str
    name: str | None = None
    description: str | None = None
    mime_type: str | None = None


class PromptModel(BaseModel):
    """Normalized representation of a single MCP prompt."""

    name: str
    description: str | None = None
    arguments: list[PromptArgument] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Server-level metadata
# ---------------------------------------------------------------------------


class ServerInfo(BaseModel):
    """Basic identity and version info from the MCP initialization handshake."""

    name: str | None = None
    version: str | None = None
    protocol_version: str | None = None


class ServerCapabilities(BaseModel):
    """Which capability groups the server advertises."""

    tools: bool = False
    resources: bool = False
    prompts: bool = False


# ---------------------------------------------------------------------------
# Root model
# ---------------------------------------------------------------------------


class ServerModel(BaseModel):
    """
    The complete normalized representation of an MCP server.

    Produced by the introspection tool and consumed by every downstream
    component: rulebook, judge, reporter.
    """

    server_info: ServerInfo = Field(default_factory=ServerInfo)
    capabilities: ServerCapabilities = Field(default_factory=ServerCapabilities)
    tools: list[ToolModel] = Field(default_factory=list)
    resources: list[ResourceModel] = Field(default_factory=list)
    resource_templates: list[ResourceTemplateModel] = Field(default_factory=list)
    prompts: list[PromptModel] = Field(default_factory=list)
    # Non-fatal problems hit while listing (a timeout, a mid-session crash,
    # a refused list call). Critical for the judge: an advertised capability
    # whose listing FAILED must not be judged as "server has none" — the
    # empty list is an artifact of the failure, not a fact about the server.
    introspection_warnings: list[str] = Field(default_factory=list)

    def summary(self) -> str:
        """Human-readable one-liner summary of the server model."""
        return (
            f"Server '{self.server_info.name or 'unknown'}' v{self.server_info.version or '?'} "
            f"— {len(self.tools)} tool(s), {len(self.resources)} resource(s), "
            f"{len(self.resource_templates)} resource template(s), "
            f"{len(self.prompts)} prompt(s)"
        )
