# Portfolio Architect Gateway — DKB v1.26.1

Version 1.26.1 keeps DKB as the isolated experimental manual-only fail-closed provider shell. No DKB live acquisition/import is implemented. The ISIN-first hotfix is Home Assistant-side; the Trade Republic PDF parser and dependency remain absent from this App.

The App uses its own `/data/gateway` private volume and must be upgraded in place to retain private state.
