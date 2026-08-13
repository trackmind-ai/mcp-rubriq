---
id: S002
name: Required Array Empty
category: Schema Integrity
severity: error
annotator_flags: [required_array_empty]
---

## Rationale
LLMs may omit fields if they are not explicitly marked as required. If a tool will fail without a field, it MUST be in the `required` array.

## Pass Criteria
The tool either genuinely has all optional properties, or properly declares required ones.

## Fail Criteria
The tool has properties that are functionally mandatory, but the `required` array is empty.

## Evidence Requirement
Name a property that is obviously mandatory but missing from the `required` array.

## Union Schemas Are an Exception, Not a Violation
If the tool's schema came from a `oneOf`/`anyOf` union (`schema_is_union` is true), an
empty top-level `required` array is STRUCTURAL, not a bug: the variants may each require a
different subset of properties, so no single property is jointly mandatory across all of
them. Do not fail this rule solely because `required_array_empty` is set on a union
schema — check whether each individual branch/variant makes sense on its own instead.
