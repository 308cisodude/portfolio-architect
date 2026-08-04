# Portfolio Architect Gateway v1.19.0-rc1

Version 1.19.0-rc1 is an experimental fee-probe release candidate. The established
live portfolio, reserve, OAuth/session, REST portfolio schema 1, and health schema 5
remain compatible.

The protected admin Ingress UI adds:

- a documented instrument metadata probe for opaque `fundFlags` and eligible venues;
- a documented non-submitting ex-ante ordinary-order cost indication.

The transport permits only the exact cost-indication path. It contains no order
prevalidation, validation, quote/TAN, submission, modification, cancellation, or
generic brokerage POST facility. Probe results are sanitized, process-local, and
absent from the public portfolio and health endpoints.
