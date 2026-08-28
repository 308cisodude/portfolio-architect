# Portfolio Architect Gateway — Comdirect

Version 1.56.0 retires the temporary **Comdirect NEW** display label: this provider-qualified App is now simply **Portfolio Architect Gateway — Comdirect**. It retains the bounded one-time receiver for remaining v1.55/v1.56 legacy installations; fingerprint-pinned transfer, same-CA import, bearer preservation, OAuth-session exclusion and explicit cut-over behavior are unchanged.
This is the provider-qualified Comdirect App identity introduced for the v1.55.0 safe migration from the historical `portfolio_architect_gateway` slug to `portfolio_architect_gateway_comdirect`.

During v1.55 coexistence it was deliberately displayed as **Comdirect NEW**; from v1.56 onward this provider-qualified App is the canonical **Comdirect** App. It starts in a non-discoverable migration/setup shell, imports only allowlisted long-lived private state over one-time fingerprint-pinned TLS, preserves the historical private CA and Gateway bearer token, and deliberately does **not** copy `comdirect-session.json`. A fresh PhotoTAN bootstrap is therefore required before a migrated live-API installation can publish the new endpoint.

Do not uninstall the historical App until Portfolio Architect has explicitly confirmed the endpoint cut-over and remains healthy on this App.
