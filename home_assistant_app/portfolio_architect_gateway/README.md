# Portfolio Architect Gateway — Comdirect v1.45.0

Version 1.45.0 is package alignment for the DKB Gateway CSV acquisition release. Comdirect OAuth/session maintenance, account selection, authorized cash, provider runtime and verified-HTTPS behavior are unchanged.

Verified HTTPS/private CA trust, bearer authentication, PhotoTAN bootstrap, account
selection, request-timeout behavior, REST schema 1, health schema 6, portfolio normalization,
cached-snapshot recovery and the read-only boundary remain intact. Existing **All eligible cash**
and **Cap authorized cash** policies keep their established behavior. Common inputs such as
`1024,00`, `1024.00`, `1.024,00` and `1,024.00` are accepted at the human-facing Ingress boundary;
private persisted values remain canonical. Upgrade in place and never remove `/data/gateway` during
a normal update.
