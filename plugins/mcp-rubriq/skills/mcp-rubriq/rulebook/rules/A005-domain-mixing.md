---
id: A005
name: Domain Mixing
category: Architecture
severity: warning
annotator_flags: []
---

## Rationale
A server should have a single responsibility. Mixing completely unrelated domains makes it a monolith.

## Pass Criteria
All tools belong to a cohesive domain or system.

## Fail Criteria
The server mixes file I/O, email, and database operations together.

## Evidence Requirement
Quote tool names from at least 2 distinct, unrelated domains.
