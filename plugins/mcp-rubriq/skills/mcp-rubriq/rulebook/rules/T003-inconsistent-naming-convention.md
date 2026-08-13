---
id: T003
name: Inconsistent Naming Convention
category: Tool Quality
severity: warning
annotator_flags: [naming_inconsistent]
---

## Rationale
Inconsistent naming conventions confuse the LLM and make the server's API surface harder to predict.

## Pass Criteria
All tools use the same naming convention (e.g., all `snake_case` or all `camelCase`).

## Fail Criteria
The server mixes conventions (e.g., `read_file` alongside `writeDocument`) without a clear namespace justification.

## Evidence Requirement
Quote at least two tool names that use different conventions.
