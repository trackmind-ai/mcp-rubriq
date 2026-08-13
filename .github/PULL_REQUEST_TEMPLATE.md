## Summary

<!-- What does this PR do, and why? -->

## Which lane does this fall under?

<!-- Check the one that applies — see CONTRIBUTING.md for what each lane means. -->

- [ ] Lane A — a new/changed rule (`rulebook/rules/*.md`)
- [ ] Lane B — Python core (`introspection/`, `models/`, `rulebook/annotator.py`, `scripts/`)
- [ ] Lane C — `SKILL.md` (the judge's own instructions)
- [ ] Open lane — fixtures, docs, or a false-positive report with no code change

---

### If this is a Lane A (rule) PR

- [ ] One file, `rulebook/rules/<ID>-<slug>.md`, with the standard frontmatter
      (`id`, `name`, `category`, `severity`, `annotator_flags`) and sections
      (Rationale, Pass Criteria, Fail Criteria, Evidence Requirement)
- [ ] A paired fixture under `tests/fixtures/` that actually exhibits the pattern
- [ ] A matrix entry in `tests/test_matrix.json` exercising that fixture
- [ ] Checked `docs/boundaries.md` §A to confirm this isn't already scoped/deferred there
      with reasoning that should inform this proposal

### If this is a Lane B (Python core) PR

- [ ] `make check` passes locally (lint + typecheck + full test suite)
- [ ] If this changes a **shipped** annotator heuristic: a regression fixture proving the
      fix, checked against the existing fixture suite for reopened false positives

### If this is a Lane C (`SKILL.md`) PR

- [ ] Ran the manual adversarial check from `docs/testing.md` Layer 3 against
      `tests/fixtures/injection_metadata_server.py` — all 5 embedded hijack attempts still
      cited as evidence and not complied with
- [ ] Ran the same check against `tests/fixtures/annotations_server.py` — a tool lying about
      its own `readOnlyHint` is still treated as aggravating, not exculpatory

---

## Sign-off

- [ ] Every commit has a `Signed-off-by` trailer (`git commit -s`) — see CONTRIBUTING.md
