---
id: X003
name: Overly Broad Scope
category: Security Signals
severity: warning
annotator_flags: [has_exec_keywords]
---

## Rationale
Tools should follow the principle of least privilege. Unrestricted access (e.g., any SQL query) is dangerous.

## Pass Criteria
The description or schema defines boundaries and constraints (e.g., 'read-only', 'within workspace').

## Fail Criteria
The tool appears to grant unrestricted system-wide access without constraints.

## Evidence Requirement
Quote the tool description and identify what scope constraint is absent.

## Relationship to X004 (Command Injection Risk)
Both rules key off the same underlying signal (exec-ish keywords) and can legitimately
co-occur on the same tool, but they are distinct lenses: this rule is about the BLAST
RADIUS of what the tool can reach (e.g. an unbounded SQL query with no row/table
restriction), while X004 is about INJECTION into a string that gets executed/interpreted.
A read-only-but-unbounded query tool is X003, not X004. A tool that concatenates raw user
input into a shell/SQL string is X004, and may also be X003 if its reach is unrestricted.
Report whichever lens the actual evidence fits — don't force both to fire just because the
keyword flag is shared.
