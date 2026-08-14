# Portfolio Architect Gateway — DKB v1.26.6

Version 1.26.6 keeps DKB as the isolated experimental manual-only fail-closed provider shell while aligning package versions with Portfolio Architect's unavailable-source diagnostics hotfix. No DKB live acquisition/import is implemented, and the Trade Republic PDF parser and dependency remain absent from this App.

The App uses its own `/data/gateway` private volume and must be upgraded in place to retain private state.
