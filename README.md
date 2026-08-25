# MCP-Rubriq

[![CI](https://github.com/trackmind-ai/mcp-rubriq/actions/workflows/ci.yml/badge.svg)](https://github.com/trackmind-ai/mcp-rubriq/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-5A45FF)](https://code.claude.com/docs/en/plugins)
[![Reviewed by CodeRabbit](https://img.shields.io/coderabbit/prs/github/trackmind-ai/mcp-rubriq?utm_source=oss&utm_medium=github&utm_campaign=trackmind-ai%2Fmcp-rubriq&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)](https://coderabbit.ai)

**Grade any MCP server against a published 28-rule rubric — before an agent has to use it.**

MCP-Rubriq is a Claude Code plugin that reviews MCP (Model Context Protocol) servers the way a
careful reviewer would. It connects to a server, reads how every tool, resource, and prompt
describes itself, and scores that against an explicit rubric. What comes back is a report with a
severity per finding, the exact evidence from the server's own metadata, and a concrete fix —
plus the rules that passed and the rules that didn't apply.

Point it at a server you're building, one you're about to depend on, or one already running.

```
/mcp-rubriq test my server
```

## Why a rubric

The name is the design. MCP-Rubriq's 28 rules aren't heuristics buried in a binary — each one is
a markdown file with a stated rationale, explicit **pass criteria**, explicit **fail criteria**,
and an evidence requirement, all under
[`rulebook/rules/`](plugins/mcp-rubriq/skills/mcp-rubriq/rulebook/rules/). That shape buys three
things a conventional linter doesn't give you:

- **You can read the standard you're being held to.** Every finding names the rule it came from,
  and that rule is a file you can open, in the same repo, written to be read by a human.
- **Disagreeing with a grade is a pull request, not a bug report.** If a rule's pass/fail line is
  drawn in the wrong place for your server, the line itself is the artifact to change — see
  [`CONTRIBUTING.md`](CONTRIBUTING.md).
- **Judgment can actually be applied.** A fixed pattern can't tell a terse-but-precise
  description from a vague one. Written pass/fail criteria can be applied by a judge that reads
  the real content — which is exactly how stage 3 of the pipeline works, below.

## What it is — and what it isn't

MCP-Rubriq is a **metadata-only** reviewer. It reads what a server *declares* about itself —
names, descriptions, input schemas, MCP annotations — and grades that against the rubric using a
two-stage pipeline: a fast heuristic pass that gathers facts, followed by an LLM judge that reads
the actual content before deciding what's a real problem. Full pipeline details:
[`docs/architecture.md`](docs/architecture.md).

It **never calls a tool** and never observes runtime behavior. That's a deliberate boundary, not
a limitation we're hiding: grading declared metadata catches a large share of known MCP design
problems statically — bad naming, missing descriptions, dangerous schema shapes, undocumented
destructive actions, prompt-injection attempts embedded in metadata — but it cannot tell you
whether a tool is actually fast, actually idempotent, or genuinely behaves the way it claims to.
It also does not audit auth/transport-level security (OAuth flows, token passthrough, session
hijacking); that needs network and config inspection this tool doesn't do. The complete, reasoned
list of what's in scope and what isn't lives in [`docs/boundaries.md`](docs/boundaries.md). We'd
rather state that boundary up front than have you discover it by being surprised.

## Install

*(This section is for using MCP-Rubriq. Want to work on MCP-Rubriq's own source instead? See
[`CONTRIBUTING.md`](CONTRIBUTING.md)'s local setup, which uses `make`/`tasks.ps1`, not this.)*

**macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/trackmind-ai/mcp-rubriq/main/scripts/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/trackmind-ai/mcp-rubriq/main/scripts/install.ps1 | iex
```

One command, and it's genuinely idempotent — safe to re-run if anything below fails partway.
Here's exactly what it does, in order, so nothing happens as a surprise:

1. **Checks for the Claude Code CLI.** This is the one prerequisite that can't be automated
   away — there's nothing to install a plugin *into* without it. If it's missing, the script
   stops and points you at the Claude Code install docs instead of guessing further.
2. **Checks for `uv`, installing it if missing** (via Astral's own official installer,
   announced before it runs — nothing happens silently). `uv` is what makes the next section's
   Python prerequisite disappear: MCP-Rubriq's pipeline script carries inline dependency metadata
   ([PEP 723](https://peps.python.org/pep-0723/)), so `uv` resolves `mcp`/`pydantic`/`anyio`
   into an ephemeral environment automatically the first time you actually run `/mcp-rubriq` — no
   manual `pip install` step, ever.
3. **Registers the `trackmind` marketplace and installs MCP-Rubriq from it**, both via Claude
   Code's own non-interactive `claude plugin ...` CLI subcommands — confirmed directly (not
   assumed) that neither shows a confirmation prompt, so the whole thing runs unattended.
4. **Prints a verification command, but doesn't run it for you.** Actually grading a server
   invokes the LLM judge, which spends a small amount of real API usage — an install script
   shouldn't spend your money without you explicitly asking it to. Run it yourself once
   installed: `/mcp-rubriq test my server`.

**Prefer not to run a script, or already have things set up your way?** The two steps the
script automates are just the ordinary plugin commands, and work identically run by hand:

```
/plugin marketplace add trackmind-ai/marketplace
/plugin install mcp-rubriq@trackmind
```

The only thing you'd be opting out of is step 2 above — if you skip the script and don't have
`uv` on your machine, install the Python dependencies yourself once:

```bash
pip install -r <plugin-install-path>/skills/mcp-rubriq/introspection/requirements.txt
```

## Usage

```
/mcp-rubriq <target>
```

`<target>` can be any of:
- **A shell command that launches the server** — `python my_server.py`, `npx my-mcp-server`
- **An HTTP/SSE URL** for an already-running server — `http://localhost:8000/mcp`
- **A reference to a local, unpublished project you're building** — "test my server", "the one
  in this folder" — the most common case, and the one this tool is built around first
- **The name of a published server** — already connected in this session, or resolvable from
  MCP-Rubriq's own small registry of well-known servers (`filesystem`, `fetch`, `everything`,
  `git`, `memory`, `sqlite`, `github`, `brave-search`, `puppeteer`, `slack`). A server that
  isn't in the registry still works — you just give it as a launch command or URL.

Servers that need credentials are covered too: `--env` passes environment variables through to a
stdio-launched server, and `--header` sets a static `Authorization` header for HTTP/SSE targets.
Neither requires typing the secret into the conversation if it's already exported in your shell.

## The rubric

28 rules across five categories — full reference in [`docs/rules.md`](docs/rules.md), and the
authoritative text in [`rulebook/rules/`](plugins/mcp-rubriq/skills/mcp-rubriq/rulebook/rules/):

| Category | Rules | What it grades |
|---|---|---|
| **Tool Quality** (T) | 7 | Naming, descriptions, and MCP annotation accuracy |
| **Schema Integrity** (S) | 7 | Input-schema shape — required fields, types, format hints, bounds |
| **Architecture** (A) | 5 | Server-level surface design — too many tools, the wrong shape entirely |
| **Resource & Prompt Quality** (R) | 3 | Resources, resource templates, and prompts — a distinct surface from tool schemas |
| **Security Signals** (X) | 6 | Advisory patterns — undocumented destructive actions, credential exposure, prompt injection in metadata, cross-tool shadowing |

Severity (`error` / `warning` / `info`) tracks **quality impact**, not MCP spec conformance — the
spec marks `description` optional everywhere, but a tool an agent can't understand is still
broken in practice. Where a rule *does* map to a real spec requirement, its file says so
explicitly. X-series (security) findings are framed as advisory throughout — see
[`SECURITY.md`](SECURITY.md) for exactly what that means and doesn't mean.

## Example report

Grading MCP-Rubriq's own test fixture (`tests/fixtures/sample_server.py` — a small file-management
server with one deliberately under-documented tool) produces a real report. Abridged from an
actual run:

```
## MCP-Rubriq Report — `mcp-rubriq-test-server`

### Server Summary
A small, cohesive filesystem server with good hygiene across most of its surface —
consistent snake_case naming, fully typed schemas, correct required arrays, described
resources and prompt arguments. The quality isn't uniform, though: delete_file, the one
destructive tool, is the least documented thing on the server.

### Findings

🔴 Error — T001: Missing Tool Description
  Target: tool:delete_file
  Evidence: `description` is "" — present but empty. The other two tools are both
  described, so this is an omission, not a house style.
  Suggestion: State what it deletes, what it returns, and its failure behavior.

🔴 Error — X001: Undocumented Destructive Action   (advisory)
  Target: tool:delete_file
  Evidence: Destructive keyword "delete" in the name with an empty description, so
  every safety warning this rule requires is absent: no irreversibility statement,
  no scope, no confirmation cue.
  Suggestion: State irreversibility, bound the scope, add a confirmation cue.

🟡 Warning — T007: Annotation Mismatch (missing annotations on destructive tool)
  Target: tool:delete_file
  Evidence: `tool_annotations` is null. Nothing falsely claims readOnlyHint, so this
  is the missed-opportunity form: the tool's risk isn't machine-readable.
  Suggestion: Declare destructiveHint: true, and readOnlyHint: true on the safe tools
  so they're positively distinguishable rather than merely unannotated.

🟡 Warning — S003: Property Missing Description
  Target: tool:delete_file, property "path"
  Evidence: description is null — while the identically-named property on read_file
  is documented as "Absolute path to the file to read."
  Suggestion: Mirror the sibling tool.

🟡 Warning — X003: Overly Broad Scope   (advisory)
  Target: tool:read_file, tool:delete_file
  Evidence: Both take an unconstrained `path` with no enum, pattern, or prose limit,
  while the server publishes a `file:///workspace` resource implying a boundary the
  tools never state or enforce.
  Suggestion: Constrain paths to the workspace root — or document that they're
  deliberately unrestricted.

### Passed Rules
20 rules evaluated clean, each with its basis stated (e.g. A001: 3 tools, far below
the >20 threshold; X005: all descriptions third-person, no directives aimed at the
calling model).

### Skipped Rules
R002, S006, S007 — genuinely nothing to evaluate: no resource templates, no numeric
properties, no object-typed properties.
```

Two things worth noticing. The report never reduces the server to a single number — passed and
skipped rules are listed explicitly with their basis, so "clean" and "not applicable" stay
distinguishable, where a score would collapse both into the same digit. And four of the five
findings land on one tool, which is the actionable shape: documenting `delete_file` clears T001,
X001, S003, and T007 in a single edit.

The judge is an LLM applying written criteria, so borderline calls can shift slightly between
runs — a rule may land as a finding one run and a pass the next when the evidence genuinely sits
near the line. The rule files are what's fixed; the grade is a judgment against them.

## How it works

Three stages, every run:

1. **Introspect** — connect over `stdio`, SSE, or streamable HTTP, complete the MCP handshake, and
   list everything the server declares. Hardened against hostile or broken targets: a crash,
   garbage output, a hang, or a capability mismatch degrades to a specific error or an explicitly
   partial result, never a silently wrong one.
2. **Annotate** — a fast, deterministic pass computes *facts*, not verdicts ("this description is
   empty", "this parameter name looks like a credential"). High recall on purpose; it does not
   decide anything.
3. **Judge** — the calling LLM reads the annotated model plus all 28 rule files and grades the
   server against each applicable rule, using the annotator's flags as attention hints and the
   actual content as the evidence.

The split exists because heuristics alone can't tell context-dependent good design from a real
problem, and a judge with no heuristics re-derives the same mechanical facts from scratch every
run. Full explanation: [`docs/architecture.md`](docs/architecture.md).

## Contributing

Contributions are welcome — new rules, fixtures, false-positive reports, and documentation all
have a place. The contribution model has three lanes with different levels of review, for a
concrete reason explained up front rather than left implicit: rule files are read by the judge as
*trusted* input, which makes them a security surface, not just content. See
[`CONTRIBUTING.md`](CONTRIBUTING.md).

False-positive reports are especially welcome. For a tool whose entire product is a rubric, "this
rule is drawn in the wrong place" is the highest-value signal there is.

## Roadmap

MCP-Rubriq is public and looking for contributors. [`ROADMAP.md`](ROADMAP.md) lists what's
planned, organized by how soon it's realistic — the fastest way in is a
[good first issue](https://github.com/trackmind-ai/mcp-rubriq/labels/good%20first%20issue) or one
of the rule-content gaps it points at. [`docs/boundaries.md`](docs/boundaries.md) has the
reasoning behind each one.

The version is `0.1.0` because the rulebook and judge are still actively growing. `1.0.0` lands
once that growth settles into a stable baseline — see `CONTRIBUTING.md`'s three lanes for how
changes get reviewed on the way there.

## License

MIT — see [`LICENSE`](LICENSE).

## Security

This is a security-*adjacent* tool with an honestly-scoped boundary on what its findings can
and can't promise. Read [`SECURITY.md`](SECURITY.md) before relying on a clean report as a
safety guarantee, and see it for how to report a vulnerability privately.
