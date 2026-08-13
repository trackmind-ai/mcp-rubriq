---
id: T005
name: Invalid Name Characters/Length
category: Tool Quality
severity: error
annotator_flags: [name_invalid_chars, name_too_long]
---

## Rationale
This rule implements **SEP-986** ("Specify Format for Tool Names"), a Final/Standards-Track
MCP spec enhancement (2025-07-16): tool names SHOULD be 1-64 characters, case-sensitive,
and drawn only from `[A-Za-z0-9_.\-]`, with no spaces. SEP-986 is worded as a SHOULD, not a
hard MUST, but enforcement is increasingly strict in practice — some client SDKs now
reject non-compliant names outright at registration. Frame findings here as "violates the
naming spec (SEP-986), increasingly enforced at registration," not as an absolute
protocol-breaking error, since the underlying requirement is SHOULD-level.

## Pass Criteria
Name is 1-64 characters and contains only `[a-zA-Z0-9_\-./]`.

## Fail Criteria
Name contains spaces, colons, or exceeds 64 characters.

## Evidence Requirement
Quote the invalid tool name and state the constraint it violates.
