---
id: T004
name: Ambiguous Tool Name
category: Tool Quality
severity: warning
annotator_flags: [name_in_ambiguous_list]
---

## Rationale
Generic names like 'run' or 'process' force the LLM to rely entirely on the description and increase the chance of tool confusion.

## Pass Criteria
The name is specific to the action and target, e.g., `read_file`, `list_github_repos`.

## Fail Criteria
The name is a generic verb or noun, e.g., `run_command`, `get`, `process_data`.

## Evidence Requirement
Quote the tool name and explain why it is ambiguous.
