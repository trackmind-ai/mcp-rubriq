---
id: S004
name: Property Missing Type
category: Schema Integrity
severity: error
annotator_flags: [property_type_missing]
---

## Rationale
JSON Schema requires a `type` for robust validation. LLMs need to know if they should send a string, number, or object.

## Pass Criteria
The property declares a valid JSON Schema type.

## Fail Criteria
The property type is missing.

## Evidence Requirement
Quote the property name and state that it is missing a type. Suggest the appropriate type.
