# Portfolio Architect Gateway — DKB v1.27.4

Version 1.27.4 is package alignment for the Portfolio Architect Comdirect
session-maintenance hotfix. DKB Gateway behavior is unchanged: the App remains an
experimental manual-only fail-closed shell with provider identity `dkb` and no live
acquisition path.

Verified HTTPS/private CA trust, bearer authentication, REST schema 1, health schema
6, and DKB-vs-CSV discovery suppression remain unchanged. Upgrade in place to retain
App-private TLS state.
