---
id: S001
name: Empty Input Schema
category: Schema Integrity
severity: warning
annotator_flags: [schema_empty]
---

## Rationale
Most tools require inputs. An empty schema may indicate an incomplete definition, unless the tool explicitly takes zero arguments.

## Pass Criteria
The tool genuinely takes no arguments (e.g., `get_current_time`).

## Fail Criteria
The tool's description implies it needs inputs (e.g., 'reads a file path'), but the schema is empty.

## Evidence Requirement
Quote the description that implies inputs are needed, noting the empty schema.
