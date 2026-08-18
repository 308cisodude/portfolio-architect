# Portfolio Architect Gateway — Comdirect v1.33.1

Version 1.33.1 is package alignment for the Home Assistant-side recurring-schedule anchor
hotfix. The v1.32 diagnostic-policy audit and Comdirect runtime behavior are unchanged: authenticated upstream failures remain reduced to bounded failure classes and
approved OAuth/session rejection reasons; remote response bodies, credentials, qSession state
and private account material are not retained for diagnostics. App POST navigation remains
relative to the Ingress namespace.

Verified HTTPS/private CA trust, bearer authentication, PhotoTAN bootstrap, account
selection, authorized cash, request-timeout behavior, REST schema 1, health schema 6,
portfolio normalization, cached-snapshot recovery and the read-only boundary are
unchanged. Upgrade in place and never remove `/data/gateway` during a normal update.
