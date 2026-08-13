---
id: T002
name: Vague or Generic Description
category: Tool Quality
severity: warning
annotator_flags: [description_short, description_in_generic_list]
---

## Rationale
A description that doesn't explain *when* to call it, *what* it returns, or *how it differs* from similar tools causes the agent to either skip the tool or misuse it.

## Pass Criteria
Description clearly answers:
1. What does this tool do?
2. When should an agent call it (vs. other similar tools)?
3. What does it return?

## Fail Criteria
Description is present but does not answer at least one of the three questions above. E.g., 'Gets file data'.

## Evidence Requirement
Quote the exact description text. State which of the three criteria it fails.

## Short Is Not the Same as Vague
The annotator's `description_short` flag is a crude length heuristic (<100 characters)
meant for high recall, not a quality verdict — many good descriptions are short and
completely clear (e.g. "Reads the contents of a file at the given path."). Never fail this
rule on `description_short` alone; only fail when the description, regardless of length,
genuinely fails to answer one of the three pass-criteria questions above.
