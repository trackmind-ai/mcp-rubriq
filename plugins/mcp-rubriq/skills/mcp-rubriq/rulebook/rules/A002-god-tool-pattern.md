---
id: A002
name: God-Tool Pattern
category: Architecture
severity: warning
annotator_flags: []
---

## Rationale
A single tool that tries to do everything by taking an 'action' parameter confuses the LLM. Tools should be intent-specific.

## Pass Criteria
The tool does one clear thing, even if it requires many parameters.

## Fail Criteria
The tool takes >8 parameters and an `action`/`mode` parameter that drastically changes its behavior.

## Evidence Requirement
Quote the tool name, parameter count, and the `action`/`mode` parameter.

## Resolving Consolidation with A001 (Tool Bloat)
This rule and A001 pull in opposite-looking directions and must not be applied
independently of each other. A server flagged for tool bloat should NEVER be told to
consolidate by adding an `action`/`mode` switch — that trades many small problems for one
God-Tool. The correct consolidation is by outcome/intent (see A001's resolution note): if
a proposed A001 fix would trip this rule, it is not a valid fix.
