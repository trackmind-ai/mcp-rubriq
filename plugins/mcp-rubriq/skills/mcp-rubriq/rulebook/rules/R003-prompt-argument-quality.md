---
id: R003
name: Prompt Argument Quality
category: Resource & Prompt Quality
severity: warning
annotator_flags: [description_missing, name_ambiguous]
---

## Rationale
A prompt argument is `{name, description, required}` — NOT JSON Schema, so the S-series
schema-depth rules (type checks, format hints, bounds) don't apply here. But the same
underlying problem T001/S003 address for tools applies to prompt arguments: an argument
marked `required` with no description, or named ambiguously (`x`, `fmt`, `val`), forces
the caller to guess what value is expected.

## Pass Criteria
Every argument either has a clear description, or its name alone is unambiguous (e.g.
`city`, `start_date`). A `required` argument in particular should never be left
undescribed — the caller cannot skip it, so guessing wrong is guaranteed friction.

## Fail Criteria
An argument's description is missing AND its name is ambiguous (single-letter or from the
generic list), OR a `required` argument has no description at all regardless of its name.

## Evidence Requirement
Quote the prompt name, the argument name, its `required` value, and state that its
description is missing (and, if applicable, that its name is also ambiguous).
