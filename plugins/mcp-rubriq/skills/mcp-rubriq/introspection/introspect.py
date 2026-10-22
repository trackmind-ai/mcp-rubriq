# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: GPL-3.0-or-later

"""
introspection/introspect.py

MCP-Rubriq introspection tool.

Connects to a target MCP server (via stdio, SSE, or streamable HTTP), performs
the initialization handshake, retrieves all exposed tools, resources, and
prompts, maps them into the MCP-Rubriq ServerModel, and prints the result as JSON
to stdout.

Exit codes:
  0 — success, JSON ServerModel on stdout
  1 — connection or protocol error, JSON error object on stderr

Usage:
  python introspect.py --transport stdio --command "python my_server.py"
  python introspect.py --transport stdio --command "npx" \
      --args "@modelcontextprotocol/server-filesystem" "/tmp"
  python introspect.py --transport stdio --command "npx" --env GITHUB_TOKEN=ghp_xxx \
      --args "-y" "@modelcontextprotocol/server-github"
  python introspect.py --transport sse --url "http://localhost:8000/sse"
  python introspect.py --transport http --url "http://localhost:8000/mcp"

  # A path argument containing a space (common on Windows) is ambiguous when
  # embedded unquoted in --command — use --args to pass it as its own token.
  # --args MUST be the last flag: it consumes every remaining token literally
  # (via argparse.REMAINDER), including dash-prefixed ones like npx's -y, so
  # anything after it would otherwise be silently swallowed into this list
  # instead of being parsed as --env/--timeout/etc.
  python introspect.py --transport stdio --command "npx" --args "-y" \
      "@modelcontextprotocol/server-filesystem" "C:\\Users\\Jane Doe\\project"
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import shlex
import sys
import tempfile
from typing import Any, NoReturn, TextIO, cast

import anyio
import httpx

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup  # noqa: F811 (builtin shim for <3.11)

# Ensure the project root is on the path so models can be imported
# regardless of where the script is called from.
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import get_default_environment, stdio_client
from mcp.client.streamable_http import streamable_http_client

# create_mcp_http_client lives in mcp's own private module and is only
# re-exported (unofficially) via mcp.client.streamable_http, which doesn't
# declare it in __all__ — importing it from there works at runtime but isn't
# part of mcp's public API contract, so a future mcp release could rename or
# drop that re-export without it counting as a breaking change on their end.
# Import from the real location directly instead of relying on the accident.
from mcp.shared._httpx_utils import create_mcp_http_client

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.server_model import (
    PromptArgument,
    PromptModel,
    ResourceModel,
    ResourceTemplateModel,
    ServerCapabilities,
    ServerInfo,
    ServerModel,
    ToolAnnotations,
    ToolInputProperty,
    ToolInputSchema,
    ToolModel,
)

# ---------------------------------------------------------------------------
# Error unwrapping
#
# anyio's TaskGroup machinery (used internally by stdio_client/sse_client/
# streamable_http_client) wraps any exception raised inside it in one or more
# layers of ExceptionGroup — e.g. a plain TimeoutError from anyio.fail_after()
# arrives as ExceptionGroup(ExceptionGroup(TimeoutError())). Left unwrapped,
# this defeats `except TimeoutError` entirely and collapses every failure
# mode (timeout, closed connection, crashed process) into the same opaque
# "unhandled errors in a TaskGroup (1 sub-exception)" message.
# ---------------------------------------------------------------------------


class ServerConnectionError(Exception):
    """The MCP connection failed for a reason other than a timeout. Carries
    the unwrapped underlying exception and, for stdio, any text the child
    process wrote to stderr — usually the only real diagnostic available
    (e.g. an npm 404, a Python traceback from a missing dependency)."""


def _unwrap_exception_group(exc: BaseException) -> BaseException:
    """Descend through nested single-child ExceptionGroups to the leaf
    exception that actually explains the failure."""
    while isinstance(exc, BaseExceptionGroup) and len(exc.exceptions) == 1:
        exc = exc.exceptions[0]
    return exc


def _reraise_unwrapped(exc: BaseExceptionGroup, stderr_text: str = "") -> NoReturn:
    leaf = _unwrap_exception_group(exc)
    if isinstance(leaf, TimeoutError):
        raise TimeoutError() from None
    message = f"{type(leaf).__name__}: {leaf}" if str(leaf) else type(leaf).__name__
    if stderr_text:
        message += f" | server stderr: {stderr_text}"
    raise ServerConnectionError(message) from leaf


# ---------------------------------------------------------------------------
# Schema resolution
#
# A tool's inputSchema/outputSchema is a JSON Schema object, but _map_tool
# used to only ever read its top-level `properties`/`required` keys. Any
# schema built from a Pydantic or Zod model tends to express its shape via
# `$ref` into a `$defs`/`definitions` block, `allOf` composition, or a
# `oneOf`/`anyOf` union instead — all of which have NO top-level `properties`
# key at all, so they read as "empty" (false S001) even though they're fully
# specified.
# ---------------------------------------------------------------------------


def _resolve_ref(ref: str, defs: dict) -> dict:
    """Resolve a local JSON Schema $ref like '#/$defs/Name' against the
    already-collected defs map. Non-local refs (pointing outside this
    document) aren't resolvable without a fetch and are left as-is."""
    if not ref.startswith("#/"):
        return {}
    name = ref.rsplit("/", 1)[-1]
    return defs.get(name, {})


def _resolve_schema(schema: dict, _depth: int = 0) -> dict:
    """Best-effort flatten a JSON Schema node into a plain
    {type, properties, required, ...} shape:
      - $ref is resolved against the document's $defs/definitions
      - allOf branches are merged into one property set
      - oneOf/anyOf branches are merged into the UNION of their properties
        (since the variants may have different required sets, this is
        flagged via 'x-mcp-rubriq-is-union' rather than pretending the union
        of properties is a single jointly-required shape)
    _depth guards against pathological/cyclic $ref chains.
    """
    if _depth > 10 or not isinstance(schema, dict):
        return schema if isinstance(schema, dict) else {}

    defs = {**schema.get("$defs", {}), **schema.get("definitions", {})}

    def recurse(node: dict) -> dict:
        return _resolve_schema({**node, "$defs": defs, "definitions": defs}, _depth + 1)

    if "$ref" in schema:
        return recurse(_resolve_ref(schema["$ref"], defs))

    if "allOf" in schema:
        merged_properties: dict[str, Any] = {}
        merged_required: list[str] = []
        for branch in schema["allOf"]:
            resolved_branch = recurse(branch)
            merged_properties.update(resolved_branch.get("properties", {}))
            merged_required.extend(resolved_branch.get("required", []))
        result = {k: v for k, v in schema.items() if k != "allOf"}
        result["properties"] = {**merged_properties, **schema.get("properties", {})}
        result["required"] = list(dict.fromkeys(merged_required + schema.get("required", [])))
        return result

    for union_key in ("oneOf", "anyOf"):
        if union_key in schema:
            merged_properties = {}
            for branch in schema[union_key]:
                resolved_branch = recurse(branch)
                merged_properties.update(resolved_branch.get("properties", {}))
            result = {k: v for k, v in schema.items() if k != union_key}
            result["properties"] = {**merged_properties, **schema.get("properties", {})}
            result["required"] = schema.get("required", [])
            result["x-mcp-rubriq-is-union"] = True
            return result

    return schema


# Schema keys already modeled by dedicated fields elsewhere. Everything else
# (minimum, maximum, additionalProperties, pattern, format, ...) is preserved
# into ToolInputProperty/ToolInputSchema.extra rather than silently dropped.
#
# Bugfix: extra was declared (and read by the annotator's needs_bounds check
# via "minimum" in prop_obj.extra) but NEVER populated anywhere — every
# property's extra was always {}, so needs_bounds effectively ignored real
# minimum/maximum bounds entirely and fired on keyword match alone. Found
# while wiring S007 (which needs additionalProperties surfaced the same way).
_MODELED_SCHEMA_KEYS = frozenset(
    {
        "type",
        "description",
        "enum",
        "$ref",
        "allOf",
        "oneOf",
        "anyOf",
        "properties",
        "required",
        "$defs",
        "definitions",
        "x-mcp-rubriq-is-union",
    }
)


def _build_input_schema(resolved: dict) -> ToolInputSchema:
    # A property's own value can itself be a $ref/allOf/oneOf (e.g.
    # "filters": {"$ref": "#/$defs/Filters"}) — _resolve_schema only resolves
    # the schema node it's directly called on, so without this, a property
    # like that reads as having no type/description at all (false S003/S004),
    # even though it's fully specified one level down. Reuse the same $defs
    # the top-level schema already collected (see the docstring above).
    defs = {**resolved.get("$defs", {}), **resolved.get("definitions", {})}

    properties = {}
    for prop_name, prop_data in resolved.get("properties", {}).items():
        if isinstance(prop_data, dict):
            if any(key in prop_data for key in ("$ref", "allOf", "oneOf", "anyOf")):
                prop_data = _resolve_schema({**prop_data, "$defs": defs, "definitions": defs})
            properties[prop_name] = ToolInputProperty(
                type=prop_data.get("type"),
                description=prop_data.get("description"),
                enum=prop_data.get("enum"),
                extra={k: v for k, v in prop_data.items() if k not in _MODELED_SCHEMA_KEYS},
            )
        else:
            properties[prop_name] = ToolInputProperty()

    return ToolInputSchema(
        type=resolved.get("type", "object"),
        properties=properties,
        required=resolved.get("required", []),
        is_union=resolved.get("x-mcp-rubriq-is-union", False),
        extra={k: v for k, v in resolved.items() if k not in _MODELED_SCHEMA_KEYS},
    )


# ---------------------------------------------------------------------------
# Mapping helpers: raw MCP SDK → MCP-Rubriq models
# ---------------------------------------------------------------------------


def _map_tool(raw: Any) -> ToolModel:
    """Map a raw MCP Tool object into a ToolModel."""
    raw_schema = getattr(raw, "inputSchema", None) or {}
    if hasattr(raw_schema, "model_dump"):
        # raw_schema's real type here is whatever the MCP SDK's dynamically-typed
        # Tool.inputSchema attribute happens to be at runtime (usually already a
        # dict, occasionally a pydantic model) — cast rather than fight pyright's
        # dict-shaped inference of the `or {}` fallback above.
        raw_schema = cast(Any, raw_schema).model_dump()
    input_schema = _build_input_schema(_resolve_schema(raw_schema))

    raw_output_schema = getattr(raw, "outputSchema", None)
    output_schema = None
    if raw_output_schema:
        if hasattr(raw_output_schema, "model_dump"):
            raw_output_schema = raw_output_schema.model_dump()
        output_schema = _build_input_schema(_resolve_schema(raw_output_schema))

    return ToolModel(
        name=raw.name,
        description=getattr(raw, "description", None),
        input_schema=input_schema,
        output_schema=output_schema,
        tool_annotations=_map_tool_annotations(getattr(raw, "annotations", None)),
    )


def _map_tool_annotations(raw: Any) -> ToolAnnotations | None:
    """Map the raw MCP ToolAnnotations (camelCase hints) into our snake_case
    model. Returns None when the server declared no annotations block, so a
    rule can tell 'never declared' from an explicit true/false. The raw object
    can be a pydantic model or a plain dict depending on SDK path — handle both."""
    if raw is None:
        return None
    if hasattr(raw, "model_dump"):
        raw = raw.model_dump()
    if not isinstance(raw, dict):
        return None
    return ToolAnnotations(
        title=raw.get("title"),
        read_only_hint=raw.get("readOnlyHint"),
        destructive_hint=raw.get("destructiveHint"),
        idempotent_hint=raw.get("idempotentHint"),
        open_world_hint=raw.get("openWorldHint"),
    )


def _map_resource(raw: Any) -> ResourceModel:
    """Map a raw MCP Resource object into a ResourceModel."""
    return ResourceModel(
        uri=str(raw.uri),
        name=getattr(raw, "name", None),
        description=getattr(raw, "description", None),
        mime_type=getattr(raw, "mimeType", None),
    )


def _map_resource_template(raw: Any) -> ResourceTemplateModel:
    """Map a raw MCP ResourceTemplate object into a ResourceTemplateModel."""
    return ResourceTemplateModel(
        uri_template=str(raw.uriTemplate),
        name=getattr(raw, "name", None),
        description=getattr(raw, "description", None),
        mime_type=getattr(raw, "mimeType", None),
    )


def _map_prompt(raw: Any) -> PromptModel:
    """Map a raw MCP Prompt object into a PromptModel."""
    arguments = []
    for arg in getattr(raw, "arguments", None) or []:
        arguments.append(
            PromptArgument(
                name=arg.name,
                description=getattr(arg, "description", None),
                required=getattr(arg, "required", False) or False,
            )
        )
    return PromptModel(
        name=raw.name,
        description=getattr(raw, "description", None),
        arguments=arguments,
    )


# ---------------------------------------------------------------------------
# Core introspection logic
# ---------------------------------------------------------------------------


async def _introspect_session(session: ClientSession, timeout: int) -> ServerModel:
    """
    Given an already-opened ClientSession, initialize it and pull all metadata.
    Returns a fully populated ServerModel.
    """
    with anyio.fail_after(timeout):
        # Handshake
        init_result = await session.initialize()

    server_info_raw = getattr(init_result, "serverInfo", None)
    caps_raw = getattr(init_result, "capabilities", None)

    server_info = ServerInfo(
        name=getattr(server_info_raw, "name", None) if server_info_raw else None,
        version=getattr(server_info_raw, "version", None) if server_info_raw else None,
        protocol_version=getattr(init_result, "protocolVersion", None),
    )

    has_tools = caps_raw is not None and getattr(caps_raw, "tools", None) is not None
    has_resources = caps_raw is not None and getattr(caps_raw, "resources", None) is not None
    has_prompts = caps_raw is not None and getattr(caps_raw, "prompts", None) is not None

    capabilities = ServerCapabilities(
        tools=has_tools,
        resources=has_resources,
        prompts=has_prompts,
    )

    # Listing failures are non-fatal (the rest of the survey continues), but
    # they MUST be recorded in the model itself, not just printed to stderr:
    # an "empty" list caused by a failed call is indistinguishable from a
    # genuinely empty server otherwise, and the judge would confidently
    # evaluate rules (e.g. A004) against an artifact of the failure.
    warnings: list[str] = []

    def _record(what: str, exc: Exception) -> None:
        # str(TimeoutError()) is "" — fall back to the type name so the
        # warning always says WHY, never just that something failed.
        reason = str(exc).strip() or type(exc).__name__
        message = f"Could not list {what}: {reason}"
        warnings.append(message)
        _warn(message)

    async def _list_or_default(what: str, advertised: bool, list_call, extract) -> list:
        """Attempt a listing REGARDLESS of what capabilities were advertised.

        Advertisement and reality can disagree in both directions, and a
        linter must see reality:
          - A server can expose content WITHOUT advertising the capability
            (found live: an SDK server registering only a resource-templates
            handler doesn't advertise `resources`, so a capability-gated
            introspection reported zero templates). Real content behind an
            unadvertised capability is itself recorded as a warning — clients
            honoring the advertisement would never see it.
          - "Method not found" is the standard reply for an unsupported
            optional method: benign absence, no warning — UNLESS the server
            advertised the capability and then failed to implement its own
            listing (that mismatch is worth surfacing). The templates listing
            is exempt from that stricter check: it's optional WITHIN the
            resources capability, and most real servers legitimately
            advertise resources while not implementing templates/list.
        Any other failure (timeout, crash, protocol error) is recorded so the
        judge can tell a failed listing apart from a genuinely empty one.
        """
        try:
            with anyio.fail_after(timeout):
                result = await list_call()
        except Exception as exc:
            method_not_found = "method not found" in str(exc).lower()
            benign = method_not_found and (not advertised or what == "resource templates")
            if not benign:
                _record(what, exc)
            return []
        items = extract(result) or []
        if items and not advertised:
            message = (
                f"Server exposes {len(items)} {what} but does not advertise the "
                f"corresponding capability — clients honoring the advertisement "
                f"would never discover them."
            )
            warnings.append(message)
            _warn(message)
        return items

    tools = [
        _map_tool(t)
        for t in await _list_or_default("tools", has_tools, session.list_tools, lambda r: r.tools)
    ]
    resources = [
        _map_resource(r)
        for r in await _list_or_default(
            "resources", has_resources, session.list_resources, lambda r: r.resources
        )
    ]
    resource_templates = [
        _map_resource_template(t)
        for t in await _list_or_default(
            "resource templates",
            has_resources,
            session.list_resource_templates,
            lambda r: r.resourceTemplates,
        )
    ]
    prompts = [
        _map_prompt(p)
        for p in await _list_or_default(
            "prompts", has_prompts, session.list_prompts, lambda r: r.prompts
        )
    ]

    return ServerModel(
        server_info=server_info,
        capabilities=capabilities,
        tools=tools,
        resources=resources,
        resource_templates=resource_templates,
        prompts=prompts,
        introspection_warnings=warnings,
    )


async def introspect_stdio(
    command: str,
    args: list[str],
    timeout: int,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
) -> ServerModel:
    """Connect to an MCP server launched via stdio and introspect it.

    cwd matters whenever `command`/`args` reference the server by a relative
    path (e.g. `python my_server.py`) rather than an absolute one — without
    it, the child process launches with whatever directory the caller
    happened to be in, not the server's own directory, and a relative script
    path silently fails to resolve."""
    # Environment handling, three layers deliberately merged here:
    #   1. get_default_environment() — the SDK's curated safe base (PATH etc.).
    #      Passing a user env dict alone would REPLACE this base, not extend
    #      it, silently costing the child its PATH.
    #   2. UTF-8 forcing for Python-based servers. On Windows, a Python child
    #      writing to a pipe encodes with the locale code page (e.g. cp1252)
    #      by default, while the MCP client decodes strict UTF-8 — one 'é' in
    #      a tool description kills the whole session with UnicodeDecodeError
    #      (found live: tests/fixtures/unicode_server.py). PYTHONUTF8=1 fixes
    #      the encoding at the source; non-Python servers simply ignore it.
    #   3. The user's own --env pairs, last, so they win on any collision.
    full_env = get_default_environment()
    full_env["PYTHONUTF8"] = "1"
    full_env["PYTHONIOENCODING"] = "utf-8"
    if env:
        full_env.update(env)

    # encoding_error_handler="replace": if a server still emits bytes that
    # aren't valid UTF-8 (a non-Python server misconfigured to latin-1, or
    # genuine mid-stream corruption), degrade the bad bytes to U+FFFD and
    # keep linting instead of aborting the entire survey on one character.
    params = StdioServerParameters(
        command=command,
        args=args,
        env=full_env,
        cwd=cwd,
        encoding_error_handler="replace",
    )
    # errors="replace": the child's stderr arrives in whatever encoding the
    # child used (a non-Python server may write latin-1/cp1252 diagnostics);
    # reading it back must never crash the lint over one undecodable byte —
    # this exact crash happened live (UnicodeDecodeError on 0xe9) before
    # PYTHONUTF8 was forced for Python children; "replace" covers the rest.
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as errlog:
        try:
            async with stdio_client(params, errlog=cast(TextIO, errlog)) as (read, write):
                async with ClientSession(read, write) as session:
                    result = await _introspect_session(session, timeout)
        except BaseExceptionGroup as exc:
            errlog.seek(0)
            _reraise_unwrapped(exc, errlog.read().strip())
        else:
            # Success: the server's own stderr (startup banners, warnings)
            # was captured into errlog rather than passed through live —
            # forward it now so it isn't silently lost.
            errlog.seek(0)
            stderr_text = errlog.read().strip()
            if stderr_text:
                _warn(f"server stderr: {stderr_text}")
            return result


async def introspect_sse(
    url: str,
    timeout: int,
    headers: dict[str, str] | None = None,
) -> ServerModel:
    """Connect to a running MCP server via SSE and introspect it.

    headers: optional HTTP headers (e.g. Authorization: Bearer <token>) —
    without them, any auth-protected hosted server is un-lintable."""
    try:
        async with sse_client(url=url, timeout=timeout, headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                return await _introspect_session(session, timeout)
    except BaseExceptionGroup as exc:
        _reraise_unwrapped(exc)


async def introspect_http(
    url: str,
    timeout: int,
    headers: dict[str, str] | None = None,
) -> ServerModel:
    """Connect to a running MCP server via streamable HTTP and introspect it.

    headers: optional HTTP headers (e.g. Authorization: Bearer <token>) —
    without them, any auth-protected hosted server is un-lintable."""
    try:
        async with create_mcp_http_client(
            headers=headers, timeout=httpx.Timeout(timeout)
        ) as http_client:
            async with streamable_http_client(url=url, http_client=http_client) as (
                read,
                write,
                _get_session_id,
            ):
                async with ClientSession(read, write) as session:
                    return await _introspect_session(session, timeout)
    except BaseExceptionGroup as exc:
        _reraise_unwrapped(exc)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _warn(msg: str) -> None:
    print(f"[mcp-rubriq warn] {msg}", file=sys.stderr)


def _output_success(model: ServerModel) -> None:
    print(model.model_dump_json(indent=2))


def _output_error(message: str, detail: str | None = None) -> None:
    payload: dict[str, Any] = {"error": message}
    if detail:
        payload["detail"] = detail
    print(json.dumps(payload, indent=2), file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="introspect",
        description=(
            "mcp-rubriq introspection tool — connects to an MCP server and extracts its metadata."
        ),
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        required=True,
        help=(
            "Transport to use: 'stdio' to launch the server, 'sse' or 'http' to "
            "connect to a running one."
        ),
    )
    parser.add_argument(
        "--command",
        help="Shell command to launch the server (stdio only). "
        "If it contains spaces and no --args, it will be split automatically.",
    )
    parser.add_argument(
        "--args",
        nargs=argparse.REMAINDER,
        default=[],
        help="Extra arguments to pass to the command (stdio only). MUST be the last "
        "flag on the command line — it consumes every remaining token literally "
        "(including ones starting with '-', like npx's -y), so anything after "
        "it (--env, --timeout, etc.) would otherwise be silently swallowed into "
        "this list instead of being parsed as its own flag.",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Environment variable to pass to a stdio server (stdio only). Repeatable.",
    )
    parser.add_argument(
        "--cwd",
        type=str,
        default=None,
        help="Working directory to launch the stdio server in (stdio only). Required "
        "whenever --command/--args reference the server by a relative path "
        "(e.g. 'python my_server.py') and the caller's own current directory "
        "isn't the server's directory — pass the server's resolved absolute "
        "folder path so the child process finds it regardless of where this "
        "script itself was invoked from.",
    )
    parser.add_argument(
        "--url",
        help="Endpoint URL of a running MCP server (sse or http only).",
    )
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        metavar="NAME: VALUE",
        help="HTTP header to send when connecting (sse or http only). Repeatable. "
        'Example: --header "Authorization: Bearer $TOKEN". Required for any '
        "auth-protected hosted server.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Operation timeout in seconds (default: 30).",
    )
    return parser


def _parse_env(pairs: list[str]) -> dict[str, str]:
    env: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise ValueError(f"Invalid --env value {pair!r}, expected KEY=VALUE")
        env[key] = value
    return env


def _parse_headers(pairs: list[str]) -> dict[str, str]:
    """Parse repeated --header values ('Name: Value'). Split on the FIRST
    colon only — header values themselves may contain colons (URLs, base64)."""
    headers: dict[str, str] = {}
    for pair in pairs:
        name, sep, value = pair.partition(":")
        if not sep or not name.strip():
            raise ValueError(f"Invalid --header value {pair!r}, expected 'Name: Value'")
        headers[name.strip()] = value.strip()
    return headers


def split_command(command: str) -> list[str]:
    """Split a shell-style --command string into argv tokens.

    Plain shlex.split() is POSIX-mode by default, which treats backslash as
    an escape character outside quotes — silently stripping every backslash
    in an unquoted Windows path (`C:\\Users\\...` becomes `C:Users...`) and
    pointing the server at a different, still-valid-looking, wrong directory
    with no error raised.

    Splitting with posix=False preserves backslashes but leaves surrounding
    quote characters in place instead of stripping them, which is wrong the
    other way. This does both correctly: split in non-POSIX mode, then strip
    a single matching pair of leading/trailing quotes from each token.

    This does NOT fix an *unquoted* path containing a space — that is
    fundamentally ambiguous (is it one argument or two?) and needs either
    quotes in the command string or, better, --args to pass it as a
    separate token and skip string-splitting entirely.
    """
    tokens = shlex.split(command, posix=False)
    cleaned = []
    for token in tokens:
        if len(token) >= 2 and token[0] == token[-1] and token[0] in ("'", '"'):
            token = token[1:-1]
        cleaned.append(token)
    return cleaned


def _force_utf8_stdio() -> None:
    """On Windows, this process's own piped stdout/stderr default to the
    locale code page — printing a ServerModel containing CJK/emoji metadata
    would die with UnicodeEncodeError. Force UTF-8 on both streams."""
    for stream in (sys.stdout, sys.stderr):
        # isinstance, not hasattr: a replaced/captured stream (pytest, wrappers)
        # is typically not a real io.TextIOWrapper and correctly skips this —
        # isinstance also lets pyright narrow the type, unlike hasattr.
        if isinstance(stream, io.TextIOWrapper):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


def main() -> None:
    _force_utf8_stdio()
    parser = build_parser()
    cli_args = parser.parse_args()

    try:
        if cli_args.transport == "stdio":
            if not cli_args.command:
                parser.error("--command is required when --transport is stdio")

            # If --args were not provided separately, split the command string
            if cli_args.args:
                cmd = cli_args.command
                extra_args = cli_args.args
            else:
                parts = split_command(cli_args.command)
                cmd = parts[0]
                extra_args = parts[1:]

            env = _parse_env(cli_args.env) if cli_args.env else None
            model = asyncio.run(
                introspect_stdio(cmd, extra_args, cli_args.timeout, env, cli_args.cwd)
            )

        elif cli_args.transport == "sse":
            if not cli_args.url:
                parser.error("--url is required when --transport is sse")
            headers = _parse_headers(cli_args.header) if cli_args.header else None
            model = asyncio.run(introspect_sse(cli_args.url, cli_args.timeout, headers))

        elif cli_args.transport == "http":
            if not cli_args.url:
                parser.error("--url is required when --transport is http")
            headers = _parse_headers(cli_args.header) if cli_args.header else None
            model = asyncio.run(introspect_http(cli_args.url, cli_args.timeout, headers))

        else:
            parser.error(f"Unknown transport: {cli_args.transport}")
            return

        _output_success(model)
        sys.exit(0)

    except TimeoutError:
        _output_error(
            f"Connection timed out after {cli_args.timeout}s.",
            "Increase --timeout or verify the server is reachable.",
        )
        sys.exit(1)
    except Exception as exc:
        _output_error(str(exc), type(exc).__name__)
        sys.exit(1)


if __name__ == "__main__":
    main()
