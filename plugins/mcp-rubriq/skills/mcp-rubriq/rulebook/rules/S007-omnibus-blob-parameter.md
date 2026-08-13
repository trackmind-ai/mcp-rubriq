---
id: S007
name: Omnibus/Blob Parameter
category: Schema Integrity
severity: warning
annotator_flags: [is_omnibus_blob]
---

## Rationale
A catch-all object parameter with no defined shape of its own (`additionalProperties:
true` or `{}`, and no `properties` beneath it) accepts literally anything — the model can
send any keys and values it wants, and the schema provides zero validation or guidance.
This defeats the entire purpose of a JSON Schema input contract and is a common,
statically-detectable design mistake distinct from S001 (empty top-level schema) — here
the tool itself might be well-specified, but one particular property is an unconstrained
blob.

## Pass Criteria
Object-typed properties either define their own `properties`/shape, or are genuinely
meant to accept arbitrary key-value data and this is clearly documented in the
description (e.g. a `metadata` field explicitly described as "arbitrary user-defined tags").

## Fail Criteria
An object-typed property has no defined shape, `additionalProperties` is `true` (or an
empty schema `{}`), and the description does not explain that arbitrary content is
intentional.

## Evidence Requirement
Quote the tool name, the property name, and state that it accepts unconstrained
key/value data with no schema validation or documented justification.
