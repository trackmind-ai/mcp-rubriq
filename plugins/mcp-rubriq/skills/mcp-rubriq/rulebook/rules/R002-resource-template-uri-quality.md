---
id: R002
name: Resource-Template URI Quality
category: Resource & Prompt Quality
severity: warning
annotator_flags: [uri_template_valid, ambiguous_variables, scheme]
---

## Rationale
Unlike R001, this rule has teeth beyond "best practice": a resource template's
`uriTemplate` MUST be a syntactically valid **RFC 6570** URI Template, and its scheme
MUST be a valid **RFC 3986** scheme — these are spec requirements, not style preferences.
On top of that, a template with ambiguous single-letter or generic variable names (e.g.
`{x}`, `{fmt}`) tells the calling model nothing about what value to substitute, even
though the syntax itself is valid.

## Pass Criteria
`uri_template_valid` is true (balanced braces, no empty `{}`, a real scheme present), AND
every template variable has a clear, descriptive name (e.g. `{user_id}`, `{path}`,
`{commit_sha}`).

## Fail Criteria
- **Spec violation (treat as the more severe finding):** `uri_template_valid` is false —
  unbalanced braces, an empty `{}` placeholder, or no discernible URI scheme.
- **Quality issue:** the template is syntactically valid but `ambiguous_variables` is
  non-empty — one or more variables are single-letter or from the generic list (`x`,
  `fmt`, `val`, `data`, `arg`, `param`, ...).

## Evidence Requirement
Quote the exact `uriTemplate` string. For a syntax failure, state which part is
malformed (unbalanced braces / empty variable / missing scheme) and cite RFC 6570 or RFC
3986 as applicable. For an ambiguous-variable finding, quote the specific variable
name(s) flagged and suggest a descriptive replacement.
