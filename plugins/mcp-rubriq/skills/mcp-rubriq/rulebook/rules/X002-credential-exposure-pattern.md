---
id: X002
name: Credential Exposure Pattern
category: Security Signals
severity: error
annotator_flags: [credential_param]
---

## Rationale
Credentials should not be logged or echoed in responses. Descriptions suggesting otherwise indicate a security risk.

## Pass Criteria
Credential parameters explicitly state they are securely handled and not returned.

## Fail Criteria
The description implies the credential might be echoed back or logged.

## Evidence Requirement
Quote the property description indicating insecure handling.
