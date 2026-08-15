# Portfolio Architect Gateway — DKB v1.27.2

Version 1.27.2 is package alignment for the Home Assistant-side discovery-flow
hotfix. The DKB App retains the v1.27.1 persistent private-PKI HTTPS server and
Supervisor public-trust discovery boundary with the bearer-authenticated GET-only
Gateway runtime. Private CA/server keys stay under this App's isolated
`/data/gateway/tls` state.

DKB remains an experimental manual-only fail-closed provider shell with no live DKB
acquisition/import path. REST schema 1 and Gateway health schema 6 remain unchanged.

The App uses its own `/data/gateway` private volume and must be upgraded in place to
retain private state, including its TLS trust identity.
