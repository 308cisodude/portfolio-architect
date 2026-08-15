# Portfolio Architect Gateway — DKB v1.26.7

Version 1.26.7 inherits the common Gateway cached-snapshot round-trip and HTTP conditional-validator fix. DKB remains the isolated experimental manual-only fail-closed provider shell; no DKB live acquisition/import is implemented, and the Trade Republic PDF parser and dependency remain absent.

The App uses its own `/data/gateway` private volume and must be upgraded in place to retain private state.
