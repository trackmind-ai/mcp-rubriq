---
id: X004
name: Command Injection Risk
category: Security Signals
severity: warning
annotator_flags: [has_exec_keywords]
---

## Rationale
Tools that execute user-provided commands are high-risk for injection if not sanitized.

## Pass Criteria
The description mentions sanitization, parameterization, or strict allowlisting.

## Fail Criteria
The tool accepts a raw string for execution without mentioning safety boundaries.

## Evidence Requirement
Quote the property description and explain the injection risk.

## Relationship to X003 (Overly Broad Scope)
Both rules key off the same underlying signal (exec-ish keywords) and can legitimately
co-occur, but they are distinct: this rule is about raw input being concatenated into
something that gets EXECUTED/INTERPRETED (shell, SQL, an eval-like context), while X003 is
about the BLAST RADIUS of what the tool can reach regardless of injection risk. Report
whichever lens the actual evidence fits — don't force both to fire just because the
keyword flag is shared.
