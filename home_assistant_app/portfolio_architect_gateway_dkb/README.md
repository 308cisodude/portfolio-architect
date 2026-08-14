# Portfolio Architect Gateway — DKB v1.26.2

Version 1.26.2 keeps DKB as the isolated experimental manual-only fail-closed provider shell while aligning package versions with Portfolio Architect's Home Assistant-side UX/diagnostic polish. No DKB live acquisition/import is implemented, and the Trade Republic PDF parser and dependency remain absent from this App.

The App uses its own `/data/gateway` private volume and must be upgraded in place to retain private state.
