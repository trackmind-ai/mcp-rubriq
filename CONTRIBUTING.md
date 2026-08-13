# Contributing to MCP-Rubriq

Thanks for considering a contribution. This document explains **how** to contribute, and —
more importantly — **why the contribution model has two tiers**, because that shape is
deliberate, not bureaucracy for its own sake. Read the "why this lane is maintainer-gated"
notes once; they'll save you from being surprised later about why a rule PR gets more scrutiny
than a fixture PR.

The short version: the rubric is the product. A rule file isn't documentation *about* how
MCP-Rubriq grades — it *is* how MCP-Rubriq grades, read verbatim into the judge's context on
every run. That makes rule text both the most valuable thing you can contribute and the most
sensitive, and it's the reason the lanes below aren't equally open.

## Before anything else: local setup

*(This is the developer setup, for working on MCP-Rubriq's own source — it clones the repo and
builds a test/lint environment. Just want to use MCP-Rubriq? See [`README.md`](README.md)'s
Install section instead, which doesn't need any of this.)*

```bash
git clone https://github.com/trackmind-ai/mcp-rubriq.git
cd mcp-rubriq
make setup    # or: .\tasks.ps1 setup   (Windows)
make check    # or: .\tasks.ps1 check   — lint + typecheck + full test suite
```

`make check` should be clean before you open a PR. See `docs/testing.md` for what each test
layer actually proves and how to add coverage for your change.

## The three lanes

Every contribution to the rubric/judge falls into one of three lanes, and they are **not**
equally open — read the "why" below before assuming that's unfriendly.

### Lane A — Rules (`rulebook/rules/*.md`) — maintainer-reviewed

Adding or changing a rule. **Checklist for a rule PR:**

1. One file, named `<ID>-<slug>.md`, following the existing frontmatter + section structure.
   Frontmatter: `id`, `name`, `category`, `severity`, `annotator_flags` (empty list `[]` if the
   rule has no corresponding heuristic and depends entirely on the judge reading content).
   Sections, in order: `## Rationale`, `## Pass Criteria`, `## Fail Criteria`,
   `## Evidence Requirement`. Here's `T001` in full, as the reference shape:

   ```markdown
   ---
   id: T001
   name: Missing Tool Description
   category: Tool Quality
   severity: error
   annotator_flags: [description_missing]
   ---

   ## Rationale
   An agent relies entirely on a tool's description to decide when and how to call it. A
   missing description means the model must guess the tool's purpose, which often leads
   to failure.

   ## Pass Criteria
   A description is present and conveys the tool's purpose.

   ## Fail Criteria
   The description is entirely missing or consists only of whitespace.

   ## Evidence Requirement
   State that `description_missing` was flagged and the field is empty.
   ```

2. A **paired fixture** under `tests/fixtures/` that actually exhibits the pattern the rule
   checks for (and, ideally, a look-alike that shouldn't trigger it — the sharpest rule PRs
   include both).
3. A **matrix entry** in `tests/test_matrix.json` exercising the fixture.
4. If the rule needs a new annotator fact (a new flag `annotator.py` computes), that's a small,
   reviewable addition to the annotator — see Lane B below; it travels in the same PR.
5. Check `docs/boundaries.md` §A first — several rule ideas are already scoped and waiting
   (resource-annotation validity, `outputSchema` checks, the `A001` threshold, and others) with
   the reasoning for why they're not shipped yet already written down.

**Why this lane is maintainer-gated, not an open first-PR lane:** `SKILL.md` instructs the
judge to read every file in `rulebook/rules/*.md` as **trusted evaluation input**. That's the
same "text read into context and trusted" pattern rule `X005` flags as dangerous when it comes
from a target *server*. A rule file is therefore a second, less obvious prompt-injection surface
into the same judge — a maintainer reviewing a rule PR is checking not just "is this a good
rule" but "could this text manipulate the judge's own evaluation." See `SECURITY.md` for the
full framing.

### Lane B — Python core (`introspection/`, `models/`, `rulebook/annotator.py`, `scripts/`) — maintainer-reviewed

Changes to the introspection layer, the data models, the annotator's heuristics, or the CLI
entry point. These touch the contract between the three pipeline stages (see
`docs/architecture.md`), so they're maintainer-reviewed. If you're changing a **shipped**
annotator heuristic (tightening a keyword match, adjusting a threshold), include a regression
fixture proving the change fixes what you think it fixes without reopening a previously-fixed
false positive — check `docs/testing.md`'s "known environment quirks" and existing fixture
suite for prior art before assuming a pattern hasn't been hit before.

### Lane C — `SKILL.md` (the judge's own instructions) — maintainer-only

`SKILL.md` *is* the judge: it defines how targets are resolved, how the pipeline is invoked,
and how the judge is supposed to reason about the rubric and resist manipulation. A regression
here can silently break hijack-resistance or a resolution guardrail. Changes here are
maintainer-only, and before merging anything non-trivial, **run the manual adversarial check**
described in `docs/testing.md` Layer 3 — specifically, confirm the judge still resists
`tests/fixtures/injection_metadata_server.py`'s five embedded hijack attempts. This is currently
a manual step, not a CI gate (see `SECURITY.md` for why) — treat it as a required part of
review, not optional.

### The open lane — fixtures, docs, false-positive reports

Not everything needs the scrutiny above. **New fixtures**, the good-first-issue rule gaps in
`docs/boundaries.md` §A, documentation improvements, and **false-positive reports** are a fast
path: any maintainer can review and merge, normal CI + automated review is enough. False
positives especially — for a tool whose product *is* a rubric, "this rule is drawn in the wrong
place" is the highest-value signal there is, so if a rule fired
somewhere it shouldn't have, please report it (even without a fix in hand) rather than staying
quiet about it.

## Reporting a false positive

Open an issue with: which rule fired, on what tool/resource/prompt (name + the actual
description/schema text, not a paraphrase), and why it's wrong. This usually resolves into
either a rule-wording fix (Lane A) or an annotator precision fix (Lane B) — either way, it needs
your original report as the regression case.

## Sign-off: DCO, not a CLA

Every commit needs a `Signed-off-by` trailer, added automatically with:

```bash
git commit -s -m "your commit message"
```

This is a **Developer Certificate of Origin (DCO)** — a one-line certification that you wrote
the contribution (or otherwise have the right to submit it) and are licensing it under this
project's MIT license, not a separate contract to read and sign. It's enforced by an
automated check on each PR; commits missing the trailer will fail that check. We use DCO
instead of a CLA specifically to keep the "good first issue" lane genuinely low-friction — a
first-time contributor fixing a typo shouldn't hit a legal wall before their PR can merge.

## Commit and PR conventions

[Conventional Commits](https://www.conventionalcommits.org/) format (`fix:`, `feat:`, `docs:`,
`test:`, …) — this feeds an automated changelog, so it's not just style preference. Keep PRs
scoped to one lane where possible; a PR that's both a new rule and an unrelated annotator
refactor is harder to review and slower to merge than two PRs.

## Questions

Open a GitHub Discussion, or, if it's specifically about the architecture/scope boundary,
check `docs/boundaries.md` first — a good chunk of "why doesn't MCP-Rubriq do X" questions are
already answered there with the actual reasoning, not just a "no."
