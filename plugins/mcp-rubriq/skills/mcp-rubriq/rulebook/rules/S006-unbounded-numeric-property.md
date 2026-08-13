---
id: S006
name: Unbounded Numeric Property
category: Schema Integrity
severity: info
annotator_flags: [needs_bounds]
---

## Rationale
Numeric values with implicit real-world bounds (like ports or page sizes) should define `minimum`/`maximum` in the schema.

## Pass Criteria
The schema uses min/max bounds, or the value is genuinely unbounded.

## Fail Criteria
A bounded concept (like a TCP port) lacks schema bounds.

## Evidence Requirement
Quote the property name and suggest appropriate minimum/maximum bounds.
