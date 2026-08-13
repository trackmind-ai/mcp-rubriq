# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
models/annotator_model.py

Pydantic models representing the Annotated ServerModel.
These models wrap the base ServerModel with pre-computed facts (annotations).
"""

from typing import Any

from pydantic import BaseModel, Field

from models.server_model import ServerInfo


class PropertyAnnotation(BaseModel):
    type_missing: bool = False
    description_missing: bool = False
    description_short: bool = False
    needs_format_hint: bool = False
    needs_bounds: bool = False
    credential_param: bool = False
    # S007 — a bare object/untyped catch-all property (additionalProperties
    # true/{} with no defined shape of its own) that defeats schema
    # validation: the model can send anything through it.
    is_omnibus_blob: bool = False


class ToolAnnotation(BaseModel):
    description_missing: bool = False
    description_short: bool = False
    description_in_generic_list: bool = False
    name_in_ambiguous_list: bool = False
    name_invalid_chars: bool = False
    name_too_long: bool = False
    has_destructive_keywords: list[str] = Field(default_factory=list)
    has_credential_keywords: list[str] = Field(default_factory=list)
    has_exec_keywords: list[str] = Field(default_factory=list)
    has_injection_keywords: list[str] = Field(default_factory=list)
    schema_empty: bool = False
    required_array_empty: bool = False
    schema_is_union: bool = False
    properties: dict[str, PropertyAnnotation] = Field(default_factory=dict)
    # T007 (annotation mismatch) — derived by cross-referencing has_destructive_
    # keywords against tool_annotations (see AnnotatedTool). destructive_hint/
    # read_only_hint are spec-untrusted, so these are corroborating signals for
    # the judge to weigh, not proof on their own.
    annotation_missing_for_destructive_tool: bool = False
    read_only_hint_contradicts_signals: bool = False
    # X006 (cross-server / tool shadowing) — other tool names on the SAME
    # server that appear as whole words inside this tool's own description, a
    # static signal that it may be trying to reference or override them.
    references_other_tools: list[str] = Field(default_factory=list)


class AnnotatedTool(BaseModel):
    name: str
    description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] | None = None
    # `annotations` = MCP-Rubriq's OWN computed facts (below). `tool_annotations`
    # = the MCP spec's tool annotations forwarded verbatim from the server so
    # the judge can see them (untrusted hints — a server may lie). Named
    # distinctly to avoid collision with the facts field.
    tool_annotations: dict[str, Any] | None = None
    annotations: ToolAnnotation


class ServerAnnotation(BaseModel):
    tool_count: int = 0
    tool_count_high: bool = False
    has_resources: bool = False
    has_prompts: bool = False
    resource_template_count: int = 0
    naming_convention: str = "unknown"
    naming_inconsistent: bool = False
    duplicate_name_pairs: list[list[str]] = Field(default_factory=list)


# --- R-series (Resource / Prompt quality) annotation types ------------------


class ResourceAnnotation(BaseModel):
    description_missing: bool = False


class ResourceTemplateAnnotation(BaseModel):
    description_missing: bool = False
    # Lightweight RFC 6570 syntax check (balanced braces, no empty {}) plus an
    # RFC 3986 scheme presence check — not a full parser, but enough to catch
    # the realistic breakages a hand-written uriTemplate can have.
    uri_template_valid: bool = True
    # Single-letter or generic variable names (e.g. {x}, {fmt}) that don't tell
    # a caller what the variable means.
    ambiguous_variables: list[str] = Field(default_factory=list)
    scheme: str | None = None


class AnnotatedResource(BaseModel):
    uri: str
    name: str | None = None
    description: str | None = None
    mime_type: str | None = None
    annotations: ResourceAnnotation


class AnnotatedResourceTemplate(BaseModel):
    uri_template: str
    name: str | None = None
    description: str | None = None
    mime_type: str | None = None
    annotations: ResourceTemplateAnnotation


class PromptArgumentAnnotation(BaseModel):
    description_missing: bool = False
    # Single-letter or generic argument names (x, fmt, val, data...) with no
    # description to compensate.
    name_ambiguous: bool = False


class AnnotatedPromptArgument(BaseModel):
    name: str
    description: str | None = None
    required: bool = False
    annotations: PromptArgumentAnnotation


class PromptAnnotation(BaseModel):
    description_missing: bool = False


class AnnotatedPrompt(BaseModel):
    name: str
    description: str | None = None
    arguments: list[AnnotatedPromptArgument] = Field(default_factory=list)
    annotations: PromptAnnotation


class AnnotatedServerModel(BaseModel):
    server_info: ServerInfo
    server_annotations: ServerAnnotation
    tools: list[AnnotatedTool] = Field(default_factory=list)
    # Resources, resource templates, and prompts carry the same content the
    # base ServerModel has (names, descriptions, URI templates, prompt args)
    # PLUS pre-computed facts (annotations), mirroring how AnnotatedTool wraps
    # ToolModel. Top-level content fields are kept at the same paths as the
    # raw model (uri/name/description/mime_type, etc.) so existing consumers
    # reading e.g. resources[0].description are unaffected by the added
    # `annotations` sibling field.
    resources: list[AnnotatedResource] = Field(default_factory=list)
    resource_templates: list[AnnotatedResourceTemplate] = Field(default_factory=list)
    prompts: list[AnnotatedPrompt] = Field(default_factory=list)
    # Forwarded from ServerModel: non-fatal listing failures (timeout, crash
    # mid-session). When a capability's listing failed, its empty list is an
    # artifact of the failure — the judge must treat the affected counts as
    # unknown, not as evidence for rules like A004.
    introspection_warnings: list[str] = Field(default_factory=list)
