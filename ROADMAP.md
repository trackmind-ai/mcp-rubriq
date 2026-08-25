# Roadmap

`docs/boundaries.md` explains *why* something is scoped, deferred, or ruled out. This page is
the other half: *what's actually planned*, organized by how soon it's realistic, so you don't
have to reconstruct it from five different documents. If you're deciding what to work on, start
here; if you want the reasoning behind a specific item, follow the link into `boundaries.md`.

The priority order below is deliberate: MCP-Rubriq's roadmap is about making the tool itself
better — a sharper rubric, a more reliable judge, real-world coverage — before it's about
reaching more places it can run.

## Now — shipped in `0.1.0`

- 28 rules across five categories (Tool Quality, Schema Integrity, Architecture, Resource &
  Prompt Quality, Security Signals) — full list in `docs/rules.md`
- The three-stage pipeline: introspect → annotate → judge (`docs/architecture.md`)
- A Claude Code plugin, with `SKILL.md` as the judge's instructions
- Published through the shared [`trackmind-ai/marketplace`](https://github.com/trackmind-ai/marketplace)
  catalog

## Next — open for contribution right now

- **[Good first issues](https://github.com/trackmind-ai/mcp-rubriq/labels/good%20first%20issue)** —
  whatever's currently labeled; check the issue tracker, not this file, for the live list.
- **Rule-content gaps already scoped** in `docs/boundaries.md` §A: resource-annotation value
  validity, `outputSchema` checks, the `A001` tool-count threshold, finer-grained `S007`, the
  `title`-vs-`name` smell. Each has the reasoning for why it isn't shipped yet already written
  down — read that first.
- **Broader real-world server coverage** — pointing MCP-Rubriq at real, messy, non-official MCP
  servers and reporting what breaks (`docs/boundaries.md` §B). Doesn't need new code, needs
  someone's actual usage.

## Later — direction, not yet scoped

- **CI-native output** (JSON/SARIF, GitHub code-scanning integration) — natural once the rubric
  and judge behavior have had more real PRs land through it. Not started because it's not needed
  yet, not because it's rejected.
- **A community rule-plugin registry** — the long-run shape of "anyone can propose a rule," once
  the two-tier review model (`docs/boundaries.md` §D) has enough track record to trust at scale.

## Open to a contributor, not a project priority

- **Support for agent-CLI runtimes beyond Claude Code** (Codex CLI is the concrete example that
  comes up). This isn't something we're actively pursuing — the roadmap above is where our own
  effort goes. But it's a real, reviewable contribution if someone wants to drive it: build the
  equivalent judge-instruction file for that runtime, open the PR, and it goes through the same
  adversarial hijack-resistance check any `SKILL.md` change does — against the actual target
  client, at review time. See `CONTRIBUTING.md`'s Lane C for what that review covers. If you're
  considering this, open an issue first so we know someone's on it before two people duplicate
  the work.

## Not planned — a different tool, not a gap

These come up often enough to say plainly: they're architectural boundaries, not backlog items.

- **Runtime/behavioral checks** — actually calling a tool to see what it does. MCP-Rubriq reads
  declared metadata only, by design (`docs/boundaries.md` §C). Reaching this needs a call-time
  observation harness, which is a different project.
- **Auth/transport security auditing** — OAuth token passthrough, session hijacking, confused
  deputy, SSRF via discovery URLs. Needs live network/config inspection this tool doesn't do and
  isn't trying to.
- **A standalone CLI that manages its own LLM calls**, independent of any agent client. Plugging
  into an existing agent's skill/plugin system costs nothing extra and rides on a session the
  user already has. A fully standalone tool means owning API keys, billing, and a second
  invocation surface for no benefit today.

## How this gets updated

This file changes when something moves between sections — a "Next" item ships, a "Later" item
gets scoped into a concrete gap, or a genuinely new direction gets decided. It is not updated
per-PR; `CHANGELOG.md` is the record of what actually shipped.
