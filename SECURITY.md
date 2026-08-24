# Security Policy

## Reporting

Do not open public issues containing vulnerabilities, credentials, internal endpoints, customer data, source documents, prompts, or model outputs. Report findings through the private security contact designated by the project owner. The contact channel and SLA remain unresolved in M0 and are explicitly tracked as `OQ-SEC-CONTACT-001`; no public-distribution security claim may be made until they are supplied.

## Baseline

- No secrets or sensitive documents in Git.
- High-classification content must not be sent to external models.
- Authorization is enforced server-side; UI hiding is never a control.
- Raw, Draft, Review and Release access boundaries are explicit and audited.
- Connectors, parsers, model calls and Domain Packs are untrusted inputs.
- Released knowledge and evidence must remain reproducible and immutable.

See `docs/governance/SECURITY_BASELINE.md` for the full coding and release baseline.
