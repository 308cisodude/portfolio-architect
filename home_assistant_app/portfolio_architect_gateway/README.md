# Portfolio Architect Gateway — Comdirect v1.35.2

Version 1.35.2 adds the provider-owned **Keep cash reserve** authorization mode. It authorizes
only `max(eligible cash - retained EUR, 0)` while preserving the established all-available and
capped modes. The v1.35.1 connection-error classification and maintenance-worker containment remain
unchanged.

Verified HTTPS/private CA trust, bearer authentication, PhotoTAN bootstrap, account
selection, request-timeout behavior, REST schema 1, health schema 6, portfolio normalization,
cached-snapshot recovery and the read-only boundary remain intact. Existing **All eligible cash**
and **Cap authorized cash** policies keep their established behavior. Upgrade in place and never
remove `/data/gateway` during a normal update.
