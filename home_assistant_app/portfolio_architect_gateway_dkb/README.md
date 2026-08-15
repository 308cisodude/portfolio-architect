# Portfolio Architect Gateway — DKB v1.27.0

Version 1.27.0 adds the common persistent private-PKI HTTPS server and Supervisor
public-trust discovery boundary while retaining the bearer-authenticated GET-only
Gateway runtime. Private CA/server keys stay under this App's isolated
`/data/gateway/tls` state.

DKB remains an experimental manual-only fail-closed provider shell with no live DKB
acquisition/import path. REST schema 1 and Gateway health schema 6 remain unchanged.

The App uses its own `/data/gateway` private volume and must be upgraded in place to
retain private state, including its TLS trust identity.
