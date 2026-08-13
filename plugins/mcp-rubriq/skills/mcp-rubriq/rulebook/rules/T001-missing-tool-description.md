---
id: T001
name: Missing Tool Description
category: Tool Quality
severity: error
annotator_flags: [description_missing]
---

## Rationale
An agent relies entirely on a tool's description to decide when and how to call it. A missing description means the model must guess the tool's purpose, which often leads to failure.

## Pass Criteria
A description is present and conveys the tool's purpose.

## Fail Criteria
The description is entirely missing or consists only of whitespace.

## Evidence Requirement
State that `description_missing` was flagged and the field is empty.
