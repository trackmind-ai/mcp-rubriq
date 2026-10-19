# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
rulebook/annotator.py

The Annotator runs strict, high-recall heuristic checks over the ServerModel.
It does NOT produce findings. It produces an AnnotatedServerModel populated
with facts (flags) that the LLM Judge will use to evaluate the rules.
"""

import re

from models.annotator_model import (
    AnnotatedPrompt,
    AnnotatedPromptArgument,
    AnnotatedResource,
    AnnotatedResourceTemplate,
    AnnotatedServerModel,
    AnnotatedTool,
    PromptAnnotation,
    PromptArgumentAnnotation,
    PropertyAnnotation,
    ResourceAnnotation,
    ResourceTemplateAnnotation,
    ServerAnnotation,
    ToolAnnotation,
)
from models.server_model import (
    PromptModel,
    ResourceModel,
    ResourceTemplateModel,
    ServerModel,
    ToolModel,
)

# --- Keyword Lists (High Recall) ---

GENERIC_PHRASES = [
    "does stuff",
    "fetches data",
    "runs query",
    "execute",
    "helper",
    "utility",
    "handler",
    "performs action",
    "does something",
    "get data",
    "process data",
    "run command",
    "handle request",
    "do stuff",
]

AMBIGUOUS_NAMES = [
    "run",
    "execute",
    "do",
    "handle",
    "process",
    "fetch",
    "call",
    "invoke",
    "get",
    "set",
    "update",
    "post",
    "action",
    "helper",
    "util",
    "request",
    "query",
    "task",
    "job",
    "work",
]

DESTRUCTIVE_KEYWORDS = [
    "delete",
    "remove",
    "drop",
    "destroy",
    "truncate",
    "purge",
    "wipe",
    "overwrite",
    "reset",
    "erase",
    "clear",
    "kill",
    "terminate",
    "revoke",
    "modify",
    "write",
    "insert",
    "patch",
]

CREDENTIAL_KEYWORDS = [
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "auth",
    "credential",
    "private_key",
    "passphrase",
    "access_key",
]

EXEC_KEYWORDS = [
    "command",
    "cmd",
    "exec",
    "shell",
    "script",
    "eval",
    "expression",
    "query",
    "sql",
    "bash",
    "powershell",
]

# Phrases that address the calling LLM directly (second person, about its own
# instructions/permissions) rather than describing the tool for a human reader.
# A normal tool description never needs to talk to the model about what it is
# or isn't allowed to do — that's the signature of a tool-poisoning /
# prompt-injection attempt embedded in metadata. Includes concrete
# tool-poisoning patterns from the Invariant Labs catalog: hidden
# <IMPORTANT>-style directive tags, references to sensitive local paths an
# attacker wants exfiltrated, and "stash it in an odd param" exfil hints.
INJECTION_PHRASES = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "ignore your previous instructions",
    "disregard previous instructions",
    "disregard prior instructions",
    "disregard your instructions",
    "new instructions:",
    "you must now",
    "you are now allowed",
    "you now have",
    "you now can",
    "were advised to refuse",
    "do not tell the user",
    "without telling the user",
    "without informing the user",
    "override your instructions",
    "override your system prompt",
    "this is a system message",
    "act as if you",
    "your new task is",
    "you were told",
    "you were advised",
    "you do not have",
    "originally you did not",
    "<important>",
    "id_rsa",
    ".ssh/",
    ".env",
    "do not mention",
    "sidenote",
]

FORMAT_KEYWORDS = [
    "date",
    "datetime",
    "time",
    "uuid",
    "url",
    "uri",
    "email",
    "id",
    "format",
    "phone",
    "ip",
    "address",
]

BOUNDED_KEYWORDS = [
    "port",
    "count",
    "limit",
    "page",
    "timeout",
    "size",
    "length",
    "max",
    "min",
    "retry",
    "offset",
    "index",
]

# Argument/variable names too generic to convey meaning on their own — used
# by both R002 (resource-template variables) and R003 (prompt arguments).
AMBIGUOUS_VARIABLE_NAMES = {
    "x",
    "y",
    "z",
    "a",
    "b",
    "c",
    "fmt",
    "val",
    "value",
    "data",
    "arg",
    "param",
    "opt",
    "obj",
    "item",
    "thing",
}

# --- Helpers ---


def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def detect_convention(name: str) -> str:
    if "_" in name and name.islower():
        return "snake_case"
    if (
        name
        and "_" not in name
        and "-" not in name
        and name[0].islower()
        and any(c.isupper() for c in name)
    ):
        return "camelCase"
    if "-" in name and name.islower():
        return "kebab-case"
    return "unknown"


NUMERIC_SUFFIX_RE = re.compile(r"\d+$")


def strip_numeric_suffix(name: str) -> str:
    return NUMERIC_SUFFIX_RE.sub("", name)


def find_keyword_matches(text: str, keywords: list[str]) -> list[str]:
    """Match keywords on word boundaries rather than raw substrings.

    Precision fix: plain substring matching produced live false positives —
    "clear" inside "clearly", "script" inside "subscription", "id" inside
    "identifier", and "auth" inside "author" and "min" inside "administrator".

    Deliberately NOT plain \\b: regex \\b treats underscore as a word
    character, so \\bdelete\\b does NOT match inside "delete_user" — which
    would silently break detection on the single most common tool-naming
    pattern in the ecosystem (snake_case). Instead, any NON-alphanumeric
    character (including "_", "-", ".", space, or start/end of string) counts
    as a boundary, via lookaround rather than \\b.

    A narrow (s|es|d|ed) suffix is allowed between the keyword and the
    trailing boundary, so ordinary English verb conjugation still matches —
    "removes"/"deletes" (3rd-person singular), "purged"/"terminated" (past
    tense) — which a strict boundary would otherwise silently break (verified
    this does NOT reopen any of the 5 confirmed false positives above: none
    of clearly/subscription/identifier/author/administrator produce a
    keyword+allowed-suffix match, since in every case the character
    immediately after the keyword-sized prefix isn't one of s/es/d/ed).

    Deliberately NOT applied to AMBIGUOUS_NAMES/GENERIC_PHRASES, which already
    compare by exact equality, not substring.
    """
    matches = []
    for kw in keywords:
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(kw) + r"(?:s|es|d|ed)?(?![a-zA-Z0-9])"
        if re.search(pattern, text):
            matches.append(kw)
    return matches


# RFC 6570 template variables are {expr} where expr may start with an operator
# (+ # . / ; ? &) and list comma-separated names, each optionally carrying a
# :prefix or * explode modifier. This is a lightweight syntax/quality check,
# not a full RFC 6570 parser — it catches realistic breakages (unbalanced
# braces, empty {}) and low-quality variable names, which is what R002 needs.
_URI_TEMPLATE_VAR_RE = re.compile(r"\{([^{}]*)\}")
_RFC6570_OPERATORS = "+#./;?&"
_URI_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")


def extract_template_variables(uri_template: str) -> list[str]:
    names = []
    for raw in _URI_TEMPLATE_VAR_RE.findall(uri_template):
        if raw and raw[0] in _RFC6570_OPERATORS:
            raw = raw[1:]
        for part in raw.split(","):
            part = part.strip().rstrip("*").split(":")[0].strip()
            if part:
                names.append(part)
    return names


def validate_uri_template(uri_template: str) -> tuple[bool, list[str], str | None]:
    """Returns (is_valid, ambiguous_variable_names, scheme)."""
    balanced = uri_template.count("{") == uri_template.count("}")
    has_empty_var = "{}" in uri_template
    scheme_match = _URI_SCHEME_RE.match(uri_template)
    is_valid = balanced and not has_empty_var and scheme_match is not None
    variables = extract_template_variables(uri_template) if balanced else []
    ambiguous = [v for v in variables if len(v) <= 1 or v.lower() in AMBIGUOUS_VARIABLE_NAMES]
    return is_valid, ambiguous, (scheme_match.group(1) if scheme_match else None)


# --- Main Annotator Logic ---


class Annotator:
    def __init__(self, server_model: ServerModel):
        self.server = server_model

    def annotate(self) -> AnnotatedServerModel:
        server_ann = self._annotate_server()
        annotated_tools = [self._annotate_tool(t) for t in self.server.tools]

        return AnnotatedServerModel(
            server_info=self.server.server_info,
            server_annotations=server_ann,
            tools=annotated_tools,
            resources=[self._annotate_resource(r) for r in self.server.resources],
            resource_templates=[
                self._annotate_resource_template(t) for t in self.server.resource_templates
            ],
            prompts=[self._annotate_prompt(p) for p in self.server.prompts],
            introspection_warnings=self.server.introspection_warnings,
        )

    def _annotate_server(self) -> ServerAnnotation:
        tool_count = len(self.server.tools)
        resource_template_count = len(self.server.resource_templates)
        # A server can expose only templated resources and no static ones —
        # that still counts as "has resources".
        has_resources = len(self.server.resources) > 0 or resource_template_count > 0
        has_prompts = len(self.server.prompts) > 0

        # Naming convention
        conventions = set()
        for t in self.server.tools:
            c = detect_convention(t.name)
            if c != "unknown":
                conventions.add(c)

        naming_inconsistent = len(conventions) > 1
        naming_convention = (
            "mixed" if naming_inconsistent else (list(conventions)[0] if conventions else "unknown")
        )

        # Duplicate pairs (Levenshtein distance <= 2)
        duplicate_pairs = []
        names = [t.name for t in self.server.tools]
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                name_i, name_j = names[i], names[j]
                if name_i != name_j and strip_numeric_suffix(name_i) == strip_numeric_suffix(
                    name_j
                ):
                    # Sequential naming (get_item_0, get_item_1, ...) — every
                    # adjacent pair is edit-distance 1 by construction, which
                    # floods this check with false positives on a very common
                    # real naming pattern instead of catching genuine typos
                    # like get_user/get_users.
                    continue
                if levenshtein_distance(name_i, name_j) <= 2:
                    duplicate_pairs.append([name_i, name_j])

        return ServerAnnotation(
            tool_count=tool_count,
            tool_count_high=tool_count > 20,
            has_resources=has_resources,
            has_prompts=has_prompts,
            resource_template_count=resource_template_count,
            naming_convention=naming_convention,
            naming_inconsistent=naming_inconsistent,
            duplicate_name_pairs=duplicate_pairs,
        )

    def _annotate_tool(self, tool: ToolModel) -> AnnotatedTool:
        desc = tool.description or ""
        desc_strip = desc.strip()
        desc_lower = desc_strip.lower()
        name_lower = tool.name.lower()
        combined_lower = name_lower + " " + desc_lower

        ann = ToolAnnotation()
        ann.description_missing = desc_strip == ""
        ann.description_short = len(desc_strip) < 100
        ann.description_in_generic_list = desc_lower in GENERIC_PHRASES
        ann.name_in_ambiguous_list = name_lower in AMBIGUOUS_NAMES
        ann.name_invalid_chars = not bool(re.match(r"^[a-zA-Z0-9_\-./]+$", tool.name))
        ann.name_too_long = len(tool.name) > 64

        ann.has_destructive_keywords = find_keyword_matches(combined_lower, DESTRUCTIVE_KEYWORDS)
        ann.has_credential_keywords = find_keyword_matches(combined_lower, CREDENTIAL_KEYWORDS)
        ann.has_exec_keywords = find_keyword_matches(combined_lower, EXEC_KEYWORDS)
        # INJECTION_PHRASES are left on substring matching deliberately — no
        # false positive was ever found here, and several entries (".ssh/",
        # ".env") aren't standalone "words" \b would anchor sensibly anyway.
        ann.has_injection_keywords = [kw for kw in INJECTION_PHRASES if kw in desc_lower]

        # T007 — annotation mismatch (needs tool.tool_annotations, set below
        # after has_destructive_keywords so both are available together).
        ta = tool.tool_annotations
        ann.annotation_missing_for_destructive_tool = (
            bool(ann.has_destructive_keywords) and ta is None
        )
        ann.read_only_hint_contradicts_signals = bool(
            ta is not None and ta.read_only_hint is True and ann.has_destructive_keywords
        )

        # X006 — does this tool's description reference another tool on the
        # same server by name? (whole-word match against every other tool's
        # exact name.)
        other_names = [t2.name for t2 in self.server.tools if t2.name != tool.name]
        ann.references_other_tools = [
            n
            for n in other_names
            if re.search(
                r"(?<![a-zA-Z0-9])" + re.escape(n.lower()) + r"(?![a-zA-Z0-9])", desc_lower
            )
        ]

        # Schema
        schema = tool.input_schema
        properties = schema.properties if schema else {}
        required = schema.required if schema else []

        ann.schema_empty = len(properties) == 0 and len(required) == 0
        ann.required_array_empty = len(required) == 0 and len(properties) > 0
        ann.schema_is_union = schema.is_union if schema else False

        # Properties
        for prop_name, prop_obj in properties.items():
            raw_type = prop_obj.type
            # "type" may be a list (["integer", "null"]); "null" is not a shape.
            p_types = (
                [raw_type]
                if isinstance(raw_type, str)
                else [t for t in raw_type or [] if t != "null"]
            )
            p_type = (
                raw_type
                if isinstance(raw_type, str) or raw_type is None
                else (p_types[0] if len(p_types) == 1 else "union")
            )
            p_desc = prop_obj.description or ""
            p_desc_strip = p_desc.strip()
            p_combined = prop_name.lower() + " " + p_desc_strip.lower()

            p_ann = PropertyAnnotation()
            p_ann.type_missing = p_type is None
            p_ann.description_missing = p_desc_strip == ""
            p_ann.description_short = len(p_desc_strip) < 20
            p_ann.needs_format_hint = bool(find_keyword_matches(p_combined, FORMAT_KEYWORDS))

            if p_type in ("integer", "number"):
                has_bounds = ("minimum" in prop_obj.extra) or ("maximum" in prop_obj.extra)
                p_ann.needs_bounds = not has_bounds and bool(
                    find_keyword_matches(prop_name.lower(), BOUNDED_KEYWORDS)
                )

            p_ann.credential_param = bool(
                find_keyword_matches(prop_name.lower(), CREDENTIAL_KEYWORDS)
            )

            # S007 — a catch-all object property with no properties of its own
            # and additionalProperties true/{} (or genuinely untyped) admits
            # arbitrary shapes, defeating schema validation entirely.
            additional_props = prop_obj.extra.get("additionalProperties")
            has_own_shape = bool(prop_obj.extra.get("properties"))
            p_ann.is_omnibus_blob = bool(
                (p_type in ("object", None))
                and not has_own_shape
                and (
                    additional_props in (True, {})
                    or (p_type is None and additional_props is None and prop_obj.extra)
                )
            )

            ann.properties[prop_name] = p_ann

        return AnnotatedTool(
            name=tool.name,
            description=tool.description,
            input_schema=schema.model_dump() if schema else {},
            output_schema=tool.output_schema.model_dump() if tool.output_schema else None,
            # Forward the MCP spec annotations verbatim (None if the server
            # declared none) so the judge can see them. They're untrusted
            # hints (a server may lie) — the derived facts above are
            # corroborating signals, not a substitute for judge reasoning.
            tool_annotations=tool.tool_annotations.model_dump() if tool.tool_annotations else None,
            annotations=ann,
        )

    def _annotate_resource(self, resource: ResourceModel) -> AnnotatedResource:
        desc_strip = (resource.description or "").strip()
        return AnnotatedResource(
            uri=resource.uri,
            name=resource.name,
            description=resource.description,
            mime_type=resource.mime_type,
            annotations=ResourceAnnotation(description_missing=(desc_strip == "")),
        )

    def _annotate_resource_template(
        self, template: ResourceTemplateModel
    ) -> AnnotatedResourceTemplate:
        desc_strip = (template.description or "").strip()
        is_valid, ambiguous, scheme = validate_uri_template(template.uri_template)
        return AnnotatedResourceTemplate(
            uri_template=template.uri_template,
            name=template.name,
            description=template.description,
            mime_type=template.mime_type,
            annotations=ResourceTemplateAnnotation(
                description_missing=(desc_strip == ""),
                uri_template_valid=is_valid,
                ambiguous_variables=ambiguous,
                scheme=scheme,
            ),
        )

    def _annotate_prompt(self, prompt: PromptModel) -> AnnotatedPrompt:
        desc_strip = (prompt.description or "").strip()
        annotated_args = []
        for arg in prompt.arguments:
            arg_desc_strip = (arg.description or "").strip()
            annotated_args.append(
                AnnotatedPromptArgument(
                    name=arg.name,
                    description=arg.description,
                    required=arg.required,
                    annotations=PromptArgumentAnnotation(
                        description_missing=(arg_desc_strip == ""),
                        name_ambiguous=(
                            len(arg.name) <= 1 or arg.name.lower() in AMBIGUOUS_VARIABLE_NAMES
                        ),
                    ),
                )
            )
        return AnnotatedPrompt(
            name=prompt.name,
            description=prompt.description,
            arguments=annotated_args,
            annotations=PromptAnnotation(description_missing=(desc_strip == "")),
        )


def annotate(server_model: ServerModel) -> AnnotatedServerModel:
    return Annotator(server_model).annotate()
