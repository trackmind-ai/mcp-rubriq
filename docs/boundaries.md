# What's Deliberately Out of Scope, and Why

A rubric grows by default — "just add one more rule" is always tempting, and for a tool whose
core job is flagging risky patterns, it's tempting in both directions: more rules, and more
*kinds* of thing the rubric tries to grade. This document exists so that every current
boundary is a recorded decision, not a gap nobody noticed. It's organized by *why* something
is out, because the reason determines whether it's a good first contribution or a genuine
architecture change that needs a maintainer conversation before any code gets written.

## A. Rule-content gaps — good first issues

These are narrow, self-contained, don't touch the annotator/judge split's core contract, and
follow the same one-file-per-rule pattern as the 28 shipped rules (see `docs/rules.md`).
Picking one up is exactly the "open lane" described in `CONTRIBUTING.md`.

| Gap | Why it's not one of the 28 yet |
|---|---|
| **Resource-annotation value validity** — `annotations.audience` should be `user`/`assistant`, `priority` should be in `[0.0, 1.0]`, `lastModified` should be ISO-8601 | Narrow and low-incidence today — real servers rarely populate these optional fields yet. Cheap to add once it's worth the review cycle. |
| **Missing `outputSchema` / structured output** | Plenty of legitimate tools return prose, not structured data, so a blanket "should have an outputSchema" rule needs real-server evidence before the pass/fail line can be drawn without flooding false positives. |
| **Server declares tools but no `instructions`** | The MCP `initialize` response can carry optional server-wide `instructions`, currently dropped by introspection. Whether their absence is a real quality signal or just noise is genuinely unclear — best decided by whoever has actually hit this as a real gap, not speculatively. |
| **`title` vs `name` smell** — an identical, empty, or contradictory `title` field | Low value, low incidence, but a clean, tiny, well-scoped starter contribution if someone wants one. |
| **A001 threshold tuning** (currently a flat "more than ~20 tools") | A two-tier threshold (e.g. a softer signal around 15, a harder one past 25) has been discussed based on model-dependent tool-selection accuracy research, but that's secondary-source evidence, not a controlled study — changing a shipped threshold deserves firmer grounding first. |
| **Finer-grained S007** (schema anti-patterns beyond `additionalProperties` blobs — deeply-nested unconstrained arrays, `type: any` unions, …) | S007 was deliberately scoped to the one clearest, highest-confidence pattern. Broader schema-smell detection is real, but trades recall for false-positive risk fast — better built incrementally against real schemas than guessed upfront. |

None of these can regress an existing rule (they're purely additive), none require touching the
annotator/judge contract, and each should ship with its own fixture the same way every existing
rule does.

## B. Testing gaps — need real-world access, not more code

These aren't missing features — the code paths already exist and have been exercised against
everything reachable so far (see `docs/testing.md`). What's missing is broader real-world
input, which requires someone's action more than someone's code.

| Gap | What's actually needed |
|---|---|
| **Community (non-official) server sweep** | Pointing MCP-Rubriq at real, messy, non-Anthropic-maintained MCP servers and reporting what breaks. Passing the existing fixture suite and the official servers proves the *pipeline*; it can't prove every community server's idiosyncrasies are covered. |
| **Env-gated official servers** (GitHub, Brave Search, Slack) | Real API keys/tokens for the three registry entries in `known_servers.json` that need one. The corresponding matrix cases are skip-marked specifically so running them is a one-flag change, not a code change, once credentials exist. |
| **Puppeteer server** | Also deliberately skip-marked — its first run downloads a full Chromium build, which is expensive to run routinely in CI. Anyone can opt in locally when they want that specific coverage. |

## C. Architectural boundaries — not crossed on purpose

The most important section: these aren't "didn't get to it yet." They're things MCP-Rubriq's core
architecture — metadata-only, single-shot introspection (see `docs/architecture.md`) — cannot
reach *by design*. Reaching them means building a different tool, not a bigger rubric.

- **Everything behavioral.** Real error-response consistency, actual latency or response-size
  under load, whether a tool *genuinely* is idempotent or destructive rather than merely
  claiming to be. MCP-Rubriq reads definitions; it never calls a tool. This is the honest ~30% of
  known MCP anti-patterns that a metadata-only rubric cannot reach — closing it needs a
  call-time observation harness, which is a different project, not a rule addition here.
- **The auth/transport security family.** Confused-deputy problems, OAuth token passthrough,
  SSRF via OAuth discovery URLs, session hijacking, scope over-grant — all real, all requiring
  config or network inspection MCP-Rubriq doesn't do and, by design, doesn't try to. Staying out
  of that lane (and out of the official MCP Inspector's and SDK conformance tooling's lane) is
  a deliberate differentiation, not an oversight.
- **OAuth-interactive (browser-flow) authentication.** `--header` covers static credentials
  (a Bearer token, an API key); a full authorization-code-plus-PKCE browser dance needs a
  browser MCP-Rubriq never has, since it runs headlessly. Structurally out of reach, not a missing
  flag.
- **Rug-pull detection** — a server's tool definitions mutating *after* a client already
  approved them. Needs metadata snapshots compared over time; MCP-Rubriq's single-shot
  introspection has no concept of "last time." A real, different feature (a diff-and-alert
  capability) someday, not a rule today.
- **mTLS / client-certificate auth.** Theoretical only — no evidence any real MCP server
  currently requires it. Noted so it isn't silently forgotten if that changes.

The temptation with any rubric is always "just add one more rule." This section is the list
of things that look like missing checks but are actually missing *architecture* — building any
of them properly means a call-time or time-series capability, not a markdown rule file.
Conflating the two is exactly how scope creep turns a boring, reliable tool into an unreliable
one.

## D. Why rule authorship isn't a fully open first-PR lane

One structural asymmetry worth naming plainly: `SKILL.md` instructs the judge to read every
file in `rulebook/rules/*.md` as **trusted** evaluation criteria. That is the same "text read
into context and trusted" pattern `X005` flags as dangerous when it comes from a target
*server*. A community-contributed rule file is therefore a second, less obvious
prompt-injection surface into the same judge — not just a content contribution the way a new
ESLint rule usually is. That's why rule authorship (and any change to `SKILL.md` itself) stays
a maintainer-reviewed path, while fixture and documentation contributions, and the Section A
gaps above, are a much lighter, more open lane. Full detail on the two-tier model:
`CONTRIBUTING.md`; the security framing of this same fact: `SECURITY.md`.

## E. Feature scope, restated honestly

Not new information — these were out of scope from the start and remain so:

- **CI-native output** (JSON/SARIF, GitHub code-scanning integration) — a natural next phase
  once the rubric and judge behavior are stable, but a deliberate later-version scope, not a
  gap in what exists today.
- **A standalone/headless CLI.** Claude Code already provides the client and the invocation
  surface; building a second entry point duplicates it for no benefit today.
- **A community rule-plugin registry.** The eventual target end-state for the "unbounded rules"
  growth model, but Section D's reflexivity concern means it needs the two-tier review
  infrastructure in place first, not just a folder convention.
- **Automatic fixes, dashboards.** No attempt made yet; not close to needed.

## Where to start

**Adding a rule:** Section A, whichever gap you've personally hit. **Expanding real-world
confidence:** Section B — run MCP-Rubriq against a community server and report back. **Thinking
about behavioral checks, auth/transport security, or a plugin registry:** read Section C/D
first — these change what kind of tool MCP-Rubriq *is*, not just what it checks, and need a design
conversation with maintainers before any code.
