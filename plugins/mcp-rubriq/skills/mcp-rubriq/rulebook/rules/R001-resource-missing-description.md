---
id: R001
name: Resource/Template/Prompt Missing Description
category: Resource & Prompt Quality
severity: warning
annotator_flags: [description_missing]
---

## Rationale
The MCP spec marks `description` as OPTIONAL on resources, resource templates, and
prompts — so this is never a spec violation. It is still a real quality problem: an
undescribed resource, template, or prompt forces the calling model (and any human
picking from a list of them) to guess what it addresses or does purely from its `name`/
`uri`. This mirrors T001 (missing tool description) for the non-tool surfaces, unblocked
once the judge could see resource/template/prompt content rather than only their counts.

## Pass Criteria
A description is present and conveys what the resource/template/prompt is for, OR the
`name`/`uri`/`uriTemplate` is unambiguous enough on its own (e.g. a resource named
`readme` at `file:///README.md` needs no further explanation).

## Fail Criteria
The description is missing (or whitespace-only) AND the name/URI alone does not make the
resource's, template's, or prompt's purpose clear.

## Evidence Requirement
State which resource, resource template, or prompt is missing a description, quote its
`name`/`uri`/`uriTemplate`, and explain why that alone isn't sufficient.
