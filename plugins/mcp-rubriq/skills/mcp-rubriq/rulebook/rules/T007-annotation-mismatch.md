---
id: T007
name: Annotation Mismatch
category: Tool Quality
severity: warning
annotator_flags: [annotation_missing_for_destructive_tool, read_only_hint_contradicts_signals]
---

## Rationale
The MCP spec's tool `annotations` (`readOnlyHint`, `destructiveHint`, `idempotentHint`,
`openWorldHint`) are optional, machine-readable hints a server can declare about its own
tools. They are **untrusted** — the spec itself says a server can lie — so they are never
proof of anything on their own. But they are still useful corroborating metadata, and two
patterns are worth flagging:
1. A clearly destructive/mutating tool (by name or description) that declares NO
   annotations at all — a missed opportunity for the author to make the tool's risk
   machine-readable, not a security bug.
2. A tool that declares `readOnlyHint: true` while its own name/description clearly
   describes a destructive or mutating action — a direct self-contradiction that is
   either a labeling bug or a deliberate attempt to make the tool look safer to automated
   trust/consent systems than it is. **Treat the contradiction as an aggravating factor,
   never as evidence the tool is actually safe** — the annotation is exactly the thing
   under suspicion here, not a trump card.

## Pass Criteria
A tool with destructive/mutating signals in its name or description either declares no
contradicting annotation, or honestly declares `readOnlyHint: false` (and ideally
`destructiveHint: true`).

## Fail Criteria
- `read_only_hint_contradicts_signals` is true: the tool claims `readOnlyHint: true` while
  its own name/description clearly describes deleting, overwriting, or otherwise mutating
  data. This is the more severe of the two findings — do not let the annotation talk you
  out of it.
- `annotation_missing_for_destructive_tool` is true: a destructive-sounding tool declares
  no annotations block at all. Lower severity than the contradiction above — this is a
  missed-opportunity finding, not a red flag, since unannotated defaults are safe-by-design
  in the spec.

## Evidence Requirement
Quote the tool name, its description, and the exact declared annotation values (or state
that none were declared). For a contradiction finding, name specifically which words in
the name/description conflict with `readOnlyHint: true`.
