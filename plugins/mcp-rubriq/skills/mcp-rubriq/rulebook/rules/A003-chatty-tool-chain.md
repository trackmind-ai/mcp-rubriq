---
id: A003
name: Chatty Tool Chain
category: Architecture
severity: info
annotator_flags: []
---

## Rationale
If an agent must always call 3 tools in strict sequence to achieve one goal, those tools should be combined.

## Pass Criteria
Tools provide standalone value.

## Fail Criteria
Tools represent mandatory intermediate steps of a single logical operation.

## Evidence Requirement
Name the tool chain and explain why they appear sequentially mandatory.
