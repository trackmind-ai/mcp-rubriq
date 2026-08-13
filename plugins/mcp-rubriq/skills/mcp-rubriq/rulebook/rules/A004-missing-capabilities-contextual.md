---
id: A004
name: Missing Capabilities (Contextual)
category: Architecture
severity: info
annotator_flags: [has_resources=false, has_prompts=false]
---

## Rationale
If a server manages data, it should expose resources. If it has common workflows, it should expose prompts.

## Pass Criteria
The absence of resources/prompts is logically sound for the server's domain.

## Fail Criteria
The server manages static data but exposes no resources, or manages complex workflows but exposes no prompts.

## Evidence Requirement
State the server's domain and explain why resources or prompts would be expected.

## Relationship to R001-R003 (Resource & Prompt Quality)
This rule is strictly about presence/absence — should resources or prompts exist at all
given the server's domain. It says nothing about the QUALITY of resources/prompts that ARE
present; once a server has them, evaluate their descriptions, URI templates, and prompt
arguments against R001-R003 instead.
