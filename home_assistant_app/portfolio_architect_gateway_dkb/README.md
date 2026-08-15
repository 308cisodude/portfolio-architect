# Portfolio Architect Gateway — DKB v1.27.3

Version 1.27.3 aligns the DKB App package with Portfolio Architect's DKB discovery-identity hotfix. The App still publishes Gateway provider ID `dkb`; the Home Assistant integration now correctly distinguishes that identity from the established DKB CSV source ID `dkb_csv` and suppresses duplicate discovery scope.

DKB remains an experimental manual-only fail-closed provider shell with no live DKB
acquisition/import path. REST schema 1 and Gateway health schema 6 remain unchanged.

The App uses its own `/data/gateway` private volume and must be upgraded in place to
retain private state, including its TLS trust identity.
