---
id: A001
name: Tool Bloat
category: Architecture
severity: warning
annotator_flags: [tool_count_high]
---

## Rationale
Exposing too many tools degrades agent reasoning performance. It usually indicates raw API wrapping rather than outcome-focused design.

## Pass Criteria
The server has a focused, curated set of tools.

## Fail Criteria
The server exposes a massive number of granular tools (e.g., >20) that could be consolidated.

## Evidence Requirement
State the tool count and give examples of tools that could be consolidated.

## Resolving Consolidation with A002 (God-Tool Pattern)
The correct fix for tool bloat is consolidating **by outcome/intent** — fewer tools, each
still doing one clear thing (e.g. merging `list_projects`+`search_projects` into one
flexible `search_projects`, or letting `upsert_task` handle both create and update as a
single natural intent). The WRONG fix is merging many tools into one that takes an
`action`/`mode` parameter to switch behavior — that just trades tool bloat for a God-Tool
(see A002), and both must not be recommended together without this distinction. If a
consolidation suggestion here would itself trip A002, don't suggest it.
