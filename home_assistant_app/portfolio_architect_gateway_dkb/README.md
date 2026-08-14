# Portfolio Architect Gateway — DKB v1.25.0

Version 1.25.0 keeps DKB as the isolated experimental fail-closed provider shell. No DKB live acquisition/import is implemented. The Trade Republic PDF parser and dependency are deliberately absent from this App.

The App uses its own `/data/gateway` private volume and must be upgraded in place to retain private state.
