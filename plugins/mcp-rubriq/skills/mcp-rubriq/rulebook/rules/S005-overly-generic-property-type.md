---
id: S005
name: Overly Generic Property Type
category: Schema Integrity
severity: warning
annotator_flags: [needs_format_hint]
---

## Rationale
Strings used for strict formats (URLs, dates, emails) should use the `format`, `pattern`, or `enum` constraint to prevent hallucinations.

## Pass Criteria
The property provides formatting hints or constraints if it expects structured data.

## Fail Criteria
The property is a bare string but expects a strict format (e.g., an ISO-8601 date).

## Evidence Requirement
Quote the property and suggest a format constraint.
