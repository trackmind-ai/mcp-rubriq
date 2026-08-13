---
id: X001
name: Undocumented Destructive Action
category: Security Signals
severity: error
annotator_flags: [has_destructive_keywords]
---

## Rationale
Destructive actions must explicitly warn the LLM about irreversibility and scope to prevent accidental data loss.

## Pass Criteria
The description states the action is irreversible, defines the scope, and suggests confirmation.

## Fail Criteria
A destructive tool (e.g., delete) lacks safety warnings in its description.

## Evidence Requirement
Quote the tool name and description. State which safety warnings are missing.

## Using Tool Annotations as Corroborating Evidence
If the tool declares MCP spec annotations (`readOnlyHint`/`destructiveHint`), use them as
corroborating context — but annotations are UNTRUSTED (the spec itself notes a server can
lie), so they can only ever make a finding *worse*, never clear it. A tool with destructive
keywords AND an honest `destructiveHint: true` still needs the description-level safety
warnings this rule requires. A tool with destructive keywords but `readOnlyHint: true` is
a more severe case — see T007 (Annotation Mismatch) for that specific contradiction — but
still evaluate THIS rule's pass/fail purely on the description's own content, not on
whatever the tool claims about itself.
