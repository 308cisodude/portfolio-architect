# Portfolio Architect Gateway — Comdirect v1.28.0

Version 1.28.0 is package alignment for the DKB FinTS capability-probe milestone.
Comdirect runtime behavior is unchanged from the live-accepted v1.27.4 fix:
provider-specific OAuth/session maintenance runs independently of the 15-minute
portfolio acquisition cadence and performs no portfolio acquisition itself.

Verified HTTPS/private CA trust, bearer authentication, PhotoTAN bootstrap, account
selection, authorized cash, request-timeout behavior, REST schema 1, health schema 6,
portfolio normalization, cached-snapshot recovery and the read-only boundary are
unchanged. Upgrade in place and never remove `/data/gateway` during a normal update.
