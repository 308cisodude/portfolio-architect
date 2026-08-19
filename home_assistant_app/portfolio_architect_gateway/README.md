# Portfolio Architect Gateway — Comdirect v1.35.3

Version 1.35.3 aligns the Comdirect App package with the Home Assistant broker-editor menu-label
hotfix. Provider behavior is unchanged from v1.35.2: **Keep cash reserve**, all-available/capped
authorization, and the v1.35.1 connection-error/maintenance-worker resilience remain intact.

Verified HTTPS/private CA trust, bearer authentication, PhotoTAN bootstrap, account
selection, request-timeout behavior, REST schema 1, health schema 6, portfolio normalization,
cached-snapshot recovery and the read-only boundary remain intact. Existing **All eligible cash**
and **Cap authorized cash** policies keep their established behavior. Upgrade in place and never
remove `/data/gateway` during a normal update.
