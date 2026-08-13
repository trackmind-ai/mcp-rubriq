# The Rubric — Rule Reference

MCP-Rubriq grades every server against **28 rules** across five categories. This page is a
summary of each.

**This page is not the rubric.** The rubric is the set of markdown files under
`plugins/mcp-rubriq/skills/mcp-rubriq/rulebook/rules/`, one per rule, each carrying the stated
rationale, explicit pass criteria, explicit fail criteria, and evidence requirement that a judge
run actually applies. That's the authoritative source; this page is a reader's index of it
(regenerate with a frontmatter-parsing script if the two ever drift — see `docs/testing.md`).
If you want to know exactly why your server got a particular finding, open the rule file, not
this table.

**Severity** reflects quality impact, not MCP spec conformance — see `docs/architecture.md` for
why a spec-optional field (like `description`) can still be an `error`-level rule here. Where a
rule *does* encode a real spec requirement (`R002`, `T005`), its file says so explicitly, so
"the spec forbids this" stays distinguishable from "this project considers it bad design."

**Disagree with where a line is drawn?** That's a pull request against the rule file, or a
false-positive issue if you hit it on a real server — see `CONTRIBUTING.md`. A published rubric
you can't argue with would just be a linter with extra steps.

## Tool Quality (T-series) — 7 rules

Problems in how a tool names and describes itself — the primary surface an agent uses to decide
whether and how to call a tool.

| ID | Name | Severity | What it flags |
|---|---|---|---|
| T001 | Missing Tool Description | error | The description is empty or whitespace-only. An agent has nothing to decide from. |
| T002 | Vague or Generic Description | warning | A description that doesn't say *when* to call the tool, *what* it returns, or how it differs from similar tools — length alone isn't the test; a short description can still be precise. |
| T003 | Inconsistent Naming Convention | warning | The server mixes naming styles across its own tools (e.g. some `snake_case`, some `camelCase`), making the API surface harder to predict. |
| T004 | Ambiguous Tool Name | warning | A name drawn from a small set of overly generic verbs (`run`, `execute`, `process`, `get`, …) that forces the agent to rely entirely on the description. |
| T005 | Invalid Name Characters/Length | error | Violates SEP-986 (MCP's tool-naming spec enhancement): names should be 1–64 characters, case-sensitive, drawn only from `[A-Za-z0-9_.\-]`, no spaces. SEP-986 is a SHOULD, increasingly enforced server-side by SDKs at registration time. |
| T006 | Near-Duplicate Tool Names | warning | Two tool names on the same server differ by only a character or two (e.g. singular/plural), which invites tool confusion — excludes deliberate sequential naming (`get_item_0`, `get_item_1`, …). |
| T007 | Annotation Mismatch | warning | The tool's declared MCP annotations (`readOnlyHint`, `destructiveHint`, etc.) are missing where the tool is evidently destructive, or actively contradict what the name/description imply — annotations are untrusted, so a false claim is treated as aggravating, never exculpatory. |

## Schema Integrity (S-series) — 7 rules

Problems in a tool's `inputSchema` that let a model send malformed, unconstrained, or
unvalidated input.

| ID | Name | Severity | What it flags |
|---|---|---|---|
| S001 | Empty Input Schema | warning | No properties and no required fields — plausible for a genuinely zero-argument tool, suspicious otherwise. |
| S002 | Required Array Empty | error | Properties exist but none are marked `required`, so a model may omit a field the tool actually needs to function. (Exempted for `oneOf`/`anyOf` union schemas, where an empty top-level `required` is structural, not a bug.) |
| S003 | Property Missing Description | warning | A schema property with no description forces the model to guess its meaning. |
| S004 | Property Missing Type | error | JSON Schema needs a `type` for real validation — without it, the model doesn't know whether to send a string, number, or object. |
| S005 | Overly Generic Property Type | warning | A string used for a strict format (URL, date, email, UUID, …) with no `format`, `pattern`, or `enum` constraint — an open invitation for the model to hallucinate a malformed value. |
| S006 | Unbounded Numeric Property | info | A numeric field with an implicit real-world bound (a port, a page size, a timeout) that never sets `minimum`/`maximum`. |
| S007 | Omnibus/Blob Parameter | warning | A catch-all object parameter with no shape of its own (`additionalProperties: true` or `{}`, nothing under `properties`) — the model can send arbitrary keys and values, and the schema validates nothing. |

## Architecture (A-series) — 5 rules

Problems in how a server's *surface* is organized — too many tools, too few, or the wrong shape
entirely — independent of any single tool's own quality.

| ID | Name | Severity | What it flags |
|---|---|---|---|
| A001 | Tool Bloat | warning | Too many tools on one server (heuristically, more than ~20) — usually a sign of raw API-wrapping rather than outcome-focused tool design; degrades an agent's tool-selection accuracy. |
| A002 | God-Tool Pattern | warning | A single tool taking an `action`/`mode`-style parameter that fans out into unrelated behaviors — the naive "fix" for A001 that trades many small tools for one confusing one. See the cross-reference note in both rules' files: the correct fix for tool bloat is consolidating *by outcome*, never by an action switch. |
| A003 | Chatty Tool Chain | info | An agent must reliably call the same 2–3 tools in strict sequence to accomplish one goal — a sign those tools should be combined into one. |
| A004 | Missing Capabilities (Contextual) | info | A server that manages data but exposes no resources, or has common workflows but exposes no prompts. |
| A005 | Domain Mixing | warning | A server mixes clearly unrelated domains (e.g. weather and file management) into one monolith instead of a single, coherent responsibility. |

## Resource & Prompt Quality (R-series) — 3 rules

Resources, resource templates, and prompts have their own quality surface, distinct from tool
schemas — resource templates are URI-based, and prompt arguments are a flat
`{name, description, required}` list, not JSON Schema, so the S-series doesn't apply to them.

| ID | Name | Severity | What it flags |
|---|---|---|---|
| R001 | Resource/Template/Prompt Missing Description | warning | Mirrors T001 across resources, resource templates, and prompts — spec-optional, but the same discoverability problem. |
| R002 | Resource-Template URI Quality | warning (error for spec violations) | A resource template's `uriTemplate` must be a syntactically valid RFC 6570 URI Template with an RFC 3986-valid scheme — these parts *are* spec requirements, not style preferences. Also flags ambiguous single-letter template variables and a "template" with no variables at all (should be a plain resource). |
| R003 | Prompt Argument Quality | warning | A required prompt argument with no description, or an ambiguously-named one (`x`, `fmt`, `val`). |

## Security Signals (X-series) — 6 rules

Advisory security-relevant patterns in metadata. **These are signals, not a security audit** —
passing all six means nothing in the declared metadata matched these six patterns, which is a far
smaller claim than "this server is safe." See `SECURITY.md` for what the X-series can and cannot
promise, and what MCP-Rubriq's metadata-only architecture structurally cannot cover
(auth/transport security, actual runtime behavior).

| ID | Name | Severity | What it flags |
|---|---|---|---|
| X001 | Undocumented Destructive Action | error | A tool whose name/description implies a destructive, irreversible action (delete, wipe, drop, …) with no explicit warning about scope or irreversibility — corroborated, never overridden, by the tool's own (untrusted) `destructiveHint`/`readOnlyHint` annotations. |
| X002 | Credential Exposure Pattern | error | A parameter name that suggests a credential (password, token, API key, …) combined with description language implying it gets logged or echoed back. |
| X003 | Overly Broad Scope | warning | A tool that violates least-privilege — unrestricted access where a narrower interface would do (e.g. an arbitrary-SQL-query tool instead of scoped read operations). |
| X004 | Command Injection Risk | warning | A tool that executes a user-provided command/expression/query with no indication of sanitization. Overlaps X003's signal but is a distinct lens: X003 is about scope, X004 is specifically about injection surface. |
| X005 | Prompt Injection in Metadata | error | Tool, resource, or prompt metadata containing text addressed *to the calling model* — an instruction to override its own behavior, grant itself capabilities, or hide an action from the user. Metadata is read by the model as trusted context, not rendered to a human; this is tool-poisoning, not documentation, regardless of which of the four metadata surfaces it appears in. |
| X006 | Cross-Server Tool Shadowing | error | A tool's description references *another* tool by name (on the same server or a well-known tool elsewhere) in an apparent attempt to alter or override that other tool's behavior — distinct from X005, which targets the calling model directly rather than another tool. |

## See also

- `docs/architecture.md` — the annotator/judge pipeline these rules run through, and why severity tracks quality rather than spec conformance
- `docs/boundaries.md` — rule-content gaps that are open, good-first-issue contributions (e.g. resource-annotation value validity, `outputSchema` checks), and what's out of scope entirely
- `CONTRIBUTING.md` — the checklist for proposing a new rule
