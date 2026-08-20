# Portfolio Architect Gateway — Comdirect v1.38.0

Version 1.38.0 is package alignment for Portfolio Architect's Home Assistant-side dashboard usability polish. Comdirect acquisition, OAuth/session maintenance, PhotoTAN and retained-cash behavior are unchanged, including the v1.37 shared human-input helper and live-proven v1.35.4 cash syntax.

Verified HTTPS/private CA trust, bearer authentication, PhotoTAN bootstrap, account
selection, request-timeout behavior, REST schema 1, health schema 6, portfolio normalization,
cached-snapshot recovery and the read-only boundary remain intact. Existing **All eligible cash**
and **Cap authorized cash** policies keep their established behavior. Common inputs such as
`1024,00`, `1024.00`, `1.024,00` and `1,024.00` are accepted at the human-facing Ingress boundary;
private persisted values remain canonical. Upgrade in place and never remove `/data/gateway` during
a normal update.
