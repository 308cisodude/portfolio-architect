# Portfolio Architect Gateway — Comdirect v1.33.0

Version 1.33.0 is package/User-Agent alignment for the Home Assistant-side source-freshness and
plan-schedule separation release. Comdirect runtime behavior is unchanged from the live-accepted
v1.32.0 provider-diagnostics foundation.

Verified HTTPS/private CA trust, bearer authentication, PhotoTAN bootstrap, account
selection, authorized cash, request-timeout behavior, REST schema 1, health schema 6,
portfolio normalization, cached-snapshot recovery and the read-only boundary are
unchanged. Upgrade in place and never remove `/data/gateway` during a normal update.
