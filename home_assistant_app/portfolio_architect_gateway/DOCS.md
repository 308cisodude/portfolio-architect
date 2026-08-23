# Portfolio Architect Gateway — Comdirect v1.45.1

Version 1.45.1 is package alignment for the DKB legacy-migration hotfix. The common Gateway health document now represents expired cached snapshots consistently; the DKB-only migration snapshot endpoint is not enabled here. Comdirect OAuth/session maintenance, account selection, authorized cash and verified-HTTPS behavior are unchanged.

Verified HTTPS/private CA trust, bearer authentication, PhotoTAN bootstrap, account
selection, request-timeout behavior, REST schema 1, health schema 6, portfolio normalization,
cached-snapshot recovery and the read-only boundary remain intact. Existing **All eligible cash**
and **Cap authorized cash** policies keep their established behavior. Common inputs such as
`1024,00`, `1024.00`, `1.024,00` and `1,024.00` are accepted at the human-facing Ingress boundary;
private persisted values remain canonical. Upgrade in place and never remove `/data/gateway` during
a normal update.
