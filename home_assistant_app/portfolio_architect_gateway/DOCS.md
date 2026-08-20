# Portfolio Architect Gateway — Comdirect v1.37.0

Version 1.37.0 adds the shared Gateway human-numeric validation helper and migrates the existing Comdirect cash-cap/retained-reserve inputs onto its EUR primitive. The live-proven v1.35.4 accepted syntax, canonical private persistence, bounded invalid-input UX, OAuth/session maintenance and PhotoTAN behavior remain unchanged.

Verified HTTPS/private CA trust, bearer authentication, PhotoTAN bootstrap, account
selection, request-timeout behavior, REST schema 1, health schema 6, portfolio normalization,
cached-snapshot recovery and the read-only boundary remain intact. Existing **All eligible cash**
and **Cap authorized cash** policies keep their established behavior. Common inputs such as
`1024,00`, `1024.00`, `1.024,00` and `1,024.00` are accepted at the human-facing Ingress boundary;
private persisted values remain canonical. Upgrade in place and never remove `/data/gateway` during
a normal update.
