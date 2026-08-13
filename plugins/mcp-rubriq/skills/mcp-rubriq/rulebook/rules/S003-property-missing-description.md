---
id: S003
name: Property Missing Description
category: Schema Integrity
severity: warning
annotator_flags: [property_missing_description]
---

## Rationale
Properties without descriptions force the LLM to guess what value to provide.

## Pass Criteria
The property name is 100% self-explanatory (e.g., `id`), or it has a clear description.

## Fail Criteria
The property lacks a description and its name is ambiguous.

## Evidence Requirement
Quote the property name and state that its description is missing.
