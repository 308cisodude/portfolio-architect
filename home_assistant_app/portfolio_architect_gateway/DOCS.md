# Portfolio Architect Gateway — Comdirect v1.35.4

Version 1.35.4 fixes human EUR amount entry in **Investment cash authorization**. Both **Cap
authorized cash** and **Keep cash reserve** now accept common decimal comma/dot and validated
thousands-grouping forms, normalize them to canonical private state, and show bounded validation
guidance instead of a generic HTTP 400 for invalid amount syntax. The v1.35.2 policy mathematics
and v1.35.1 connection-error/maintenance-worker resilience remain intact.

Verified HTTPS/private CA trust, bearer authentication, PhotoTAN bootstrap, account
selection, request-timeout behavior, REST schema 1, health schema 6, portfolio normalization,
cached-snapshot recovery and the read-only boundary remain intact. Existing **All eligible cash**
and **Cap authorized cash** policies keep their established behavior. Common inputs such as
`1024,00`, `1024.00`, `1.024,00` and `1,024.00` are accepted at the human-facing Ingress boundary;
private persisted values remain canonical. Upgrade in place and never remove `/data/gateway` during
a normal update.
