# Portfolio Architect Gateway — Comdirect v1.35.1

Version 1.35.1 fixes the live-observed Comdirect session-maintenance resilience edge case. A direct
connection reset during OAuth refresh is now classified as a bounded retryable transport failure,
and an unexpected single maintenance-iteration exception is contained without logging exception
text or terminating the long-lived worker. Conclusive OAuth rejection semantics and interactive
PhotoTAN reauthentication remain unchanged.

Verified HTTPS/private CA trust, bearer authentication, PhotoTAN bootstrap, account
selection, authorized cash, request-timeout behavior, REST schema 1, health schema 6,
portfolio normalization, cached-snapshot recovery and the read-only boundary are
unchanged. Upgrade in place and never remove `/data/gateway` during a normal update.
