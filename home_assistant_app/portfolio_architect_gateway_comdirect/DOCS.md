# Portfolio Architect Gateway — Comdirect NEW

This is the provider-qualified Comdirect App identity introduced for the v1.55.0 safe migration from the historical `portfolio_architect_gateway` slug to `portfolio_architect_gateway_comdirect`.

During coexistence it is deliberately displayed as **Comdirect NEW**. It starts in a non-discoverable migration/setup shell, imports only allowlisted long-lived private state over one-time fingerprint-pinned TLS, preserves the historical private CA and Gateway bearer token, and deliberately does **not** copy `comdirect-session.json`. A fresh PhotoTAN bootstrap is therefore required before a migrated live-API installation can publish the new endpoint.

Do not uninstall the historical App until Portfolio Architect has explicitly confirmed the endpoint cut-over and remains healthy on this App.
