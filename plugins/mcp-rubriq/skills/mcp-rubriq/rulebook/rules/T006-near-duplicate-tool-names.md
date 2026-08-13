---
id: T006
name: Near-Duplicate Tool Names
category: Tool Quality
severity: warning
annotator_flags: [duplicate_name_pairs]
---

## Rationale
Tools with names that differ by only a character or two (e.g., singular vs plural) confuse the LLM.

## Pass Criteria
Tool names are distinct and clearly differentiable.

## Fail Criteria
Two tools have highly similar names (e.g., `get_user` and `get_users`) AND their purpose is not clearly disambiguated.

## Evidence Requirement
Quote both tool names and their descriptions to demonstrate the confusion.
