# Architecture

MCP-Rubriq is a Claude Code plugin that grades MCP (Model Context Protocol) servers against an
explicit rubric — not by calling their tools, but by reading how those tools describe themselves.
This document explains the pipeline, and the reasoning behind its three central design decisions:
the annotator/judge split, staying metadata-only, and keeping the rubric as readable markdown
rather than code.

## The pipeline: introspect → annotate → judge

A single `/mcp-rubriq <target>` invocation runs three stages:

### 1. Introspection (`introspection/introspect.py`)

Connects to the target MCP server over whichever transport it needs — `stdio` (a launched
subprocess), SSE, or streamable HTTP — completes the MCP handshake, and lists everything the
server declares: tools (with their input schemas and, if present, the spec's `readOnlyHint`
/ `destructiveHint` / `idempotentHint` / `openWorldHint` annotations), resources, resource
templates, and prompts. The output is a plain `ServerModel` — raw facts, no judgment yet.

This stage is deliberately hardened against a hostile or broken target: a server that crashes
mid-session, returns garbage, hangs, advertises a capability it doesn't implement, or
implements one it never advertised all degrade to either a clean, specific error or a
partial result explicitly marked as partial (`introspection_warnings`) — never a silent wrong
answer. See `docs/testing.md` for how that's verified.

### 2. Annotation (`rulebook/annotator.py`)

A fast, deterministic pass over the `ServerModel` that computes **facts**, not findings —
things like "this description string is empty," "this tool name is in a list of generic
verbs," "this schema's `required` array is empty while properties exist," "this parameter
name suggests a credential." The output is an `AnnotatedServerModel`: every tool, resource,
resource template, and prompt, now carrying a set of boolean/list-valued flags alongside its
original content.

The annotator is intentionally **high-recall**: it flags anything that plausibly matches a
pattern, including cases that turn out to be false positives (a `has_destructive_keywords`
flag can fire on "clear**ly**" if word-boundary matching isn't careful, for instance). It does
not decide whether a flag represents a real problem — that decision needs to see the actual
surrounding text and context, which is exactly what stage 3 does.

### 3. Judgment (the LLM, driven by `SKILL.md`)

The calling model reads the full `AnnotatedServerModel` plus every rule file under
`rulebook/rules/*.md`, then evaluates the server against each applicable rule using both the
annotator's flags *and* direct reading of the actual content. This is where recall becomes
precision: a flag is treated as an attention hint, not an automatic finding — the judge reads
the real tool name, description, and schema before deciding whether a rule actually fails, and
is explicitly instructed to evaluate every applicable rule even where the annotator raised no
flag at all (some rules, like architectural ones, have no corresponding annotator signal and
depend entirely on the judge reading the server's overall shape).

The output is a structured report: findings grouped by severity, each with the rule ID, the
target (tool/resource/prompt name), the specific evidence from the server's own metadata, and
a concrete suggested fix — plus an explicit list of rules that passed and rules that were
skipped as not applicable.

## Why split the annotator from the judge?

Two failure modes if you don't: a **pure heuristic linter** (annotator only, no judge) either
under-flags (misses anything that doesn't match a fixed pattern) or over-flags relentlessly
(every "clear" matches "clearly," every generic-sounding tool name gets flagged even when the
description makes its purpose obvious) — heuristics alone can't tell context-dependent good
design from a real problem. A **pure LLM pass with no annotator** (just hand the model the raw
server and the rubric) works, but re-derives the same mechanical facts — is the schema
empty, is the required array empty, does this key look like a credential name — from scratch
on every single run, which is slower, less consistent across runs, and leaves no structured
trail of exactly which signals fired and why a given finding was raised or dismissed.

Splitting the two gets both properties: the annotator does cheap, deterministic, complete
sweep of every candidate issue (recall), and the judge spends its reasoning budget on the part
that actually needs judgment — deciding which flagged candidates are real problems in context,
and evaluating the judgment-heavy rules the annotator can't mechanize at all (precision).

## Why metadata-only — MCP-Rubriq never calls a tool

This is the architectural line that defines what MCP-Rubriq is and isn't. Three reasons it's
drawn where it is, not just where it happened to land:

1. **Safety.** Actually invoking a server's tools to see what they do means running
   arbitrary, possibly-destructive operations from an unverified source purely to review it —
   the opposite of what a quality tool should require of you.
2. **Scope.** Whether a tool's *definition* is well-designed (a good name, an unambiguous
   description, a schema that constrains what the model can send) is a different question
   from whether the tool's *implementation* actually behaves correctly, responds quickly, or
   is genuinely as destructive/idempotent as it claims. The second question needs a call-time
   observation harness — a fundamentally different kind of tool, not a bigger rubric.
3. **Honest, bounded coverage.** Metadata alone is enough to catch a large share of known MCP
   anti-patterns statically — bad naming, missing descriptions, dangerous schema shapes,
   undocumented destructive actions, prompt-injection attempts embedded in descriptions,
   cross-tool shadowing. What it structurally cannot reach — actual runtime behavior, and the
   auth/transport security family — is documented as an intentional boundary in
   `docs/boundaries.md`, not silently ignored.

## Severity reflects quality impact, not spec conformance

The MCP spec marks `description` as *optional* everywhere — on tools, resources, prompts, and
prompt arguments. So a missing description is never technically a spec violation. MCP-Rubriq's
severities (`error` / `warning` / `info`) track **quality impact**, not the spec's MUST/SHOULD
language — which is why `T001` (missing tool description) is `error`: an agent that can't tell
what a tool does from its description will misuse or ignore it, regardless of what the spec
requires. Where a rule *does* map to an actual spec requirement — `R002`'s RFC 6570/3986
URI-template validity, `T005`'s SEP-986 naming charset — the rule text says so explicitly, so a
reader can tell "the spec forbids this" apart from "this project considers it bad design."

## Tool annotations are untrusted, always

The MCP spec lets a server declare `readOnlyHint` / `destructiveHint` / `idempotentHint` /
`openWorldHint` on each tool — but the spec itself is explicit that these are self-reported and
a server can lie. MCP-Rubriq forwards them verbatim as corroborating signal, never as proof: `T007`
treats a mismatch between a tool's declared hints and its actual name/description/behavior as a
finding in its own right, and a tool that falsely claims `readOnlyHint: true` while clearly
being destructive is scored as an *aggravating* fact by the judge, never an exculpatory one.

## Why the rubric is markdown, one file per rule

Every rule lives in its own file under `rulebook/rules/`, named `<ID>-<slug>.md`, with a fixed
structure: YAML frontmatter (`id`, `name`, `category`, `severity`, `annotator_flags`), then
Rationale, Pass Criteria, Fail Criteria, and an Evidence Requirement section.

**Markdown rather than code** is the load-bearing choice, and it follows directly from stage 3.
The judge is an LLM applying written criteria, so the criteria have to be *written* — a rule
expressed as a regex or a predicate function could only be executed, not reasoned with, and
would collapse the judge back into the pure-heuristic failure mode described above. Making the
rubric prose has a second effect that matters just as much: the standard a server is graded
against is legible to the person receiving the grade. They can read the rule, disagree with where
its pass/fail line sits, and propose a different line. That's the whole premise of the project's
name, and it's why `docs/rules.md` is a summary of the rubric rather than its source of truth.

**One file per rule** costs essentially nothing in practice — the judge reads every rule file on
every run regardless of whether they're split or combined, and the full rubric is a few thousand
tokens total — while buying a clean 1:1 mapping from rule ID to file, simple git history per
rule, and a contribution unit that's trivial to review in isolation (see `CONTRIBUTING.md`'s
rule-lane checklist).

The cost is that trusted-prose-in-context is also an injection surface. That's a managed
trade-off, not an oversight: see `SECURITY.md` and `docs/boundaries.md` §D.

## Transports and auth

MCP-Rubriq grades any MCP server reachable via `stdio` (a command it launches itself), `sse`, or
streamable `http`. For a target's own downstream secrets (an API key the *server* needs, like
`GITHUB_TOKEN`), `--env` passes environment variables to a stdio-launched server. For a static
auth gate on the MCP connection itself (an `Authorization: Bearer …` header a hosted server
requires), `--header` works on both HTTP and SSE. Neither ever needs the literal secret typed
into the conversation if it's already exported in your own shell — see `SKILL.md` for the
exact invocation forms.

## See also

- `docs/rules.md` — the full rule reference
- `docs/boundaries.md` — what's deliberately out of scope, and why
- `docs/testing.md` — how the pipeline and the judge are tested, and how to run those tests yourself
