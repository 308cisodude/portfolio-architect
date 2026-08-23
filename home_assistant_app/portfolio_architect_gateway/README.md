# Portfolio Architect Gateway — Comdirect v1.47.0

Version 1.47.0 is package alignment for DKB provider-scoped Girokonto cash evidence. Comdirect OAuth/session maintenance, account selection, authorized cash, cached-snapshot behavior and verified-HTTPS serving are unchanged.

Verified HTTPS/private CA trust, bearer authentication, PhotoTAN bootstrap, account
selection, request-timeout behavior, REST schema 1, health schema 6, portfolio normalization,
cached-snapshot recovery and the read-only boundary remain intact. Existing **All eligible cash**
and **Cap authorized cash** policies keep their established behavior. Common inputs such as
`1024,00`, `1024.00`, `1.024,00` and `1,024.00` are accepted at the human-facing Ingress boundary;
private persisted values remain canonical. Upgrade in place and never remove `/data/gateway` during
a normal update.
