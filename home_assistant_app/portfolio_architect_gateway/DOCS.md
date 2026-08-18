# Portfolio Architect Gateway — Comdirect v1.35.0

Version 1.35.0 is package/User-Agent alignment for provider-scoped funding. The Comdirect
Gateway continues to publish only its own provider-owned authorized investment cash through the
unchanged REST schema 1 contract; the Home Assistant integration is responsible for keeping that
cash separate from other providers and for advisory funding-route planning. Comdirect acquisition,
OAuth/session maintenance and provider diagnostics are unchanged.

Verified HTTPS/private CA trust, bearer authentication, PhotoTAN bootstrap, account
selection, authorized cash, request-timeout behavior, REST schema 1, health schema 6,
portfolio normalization, cached-snapshot recovery and the read-only boundary are
unchanged. Upgrade in place and never remove `/data/gateway` during a normal update.
