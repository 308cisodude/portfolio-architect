# Portfolio Architect Gateway — Comdirect v1.27.3

Version 1.27.3 is package alignment for the Portfolio Architect DKB discovery-identity hotfix; Comdirect Gateway TLS/runtime, acquisition, OAuth/session, PhotoTAN, account selection and authorized-cash behavior are unchanged from v1.27.2.

Comdirect acquisition, OAuth/session, PhotoTAN, account selection, authorized cash,
REST schema 1 and health schema 6 are unchanged. Upgrade the Portfolio Architect
Home Assistant integration to 1.27.3 before updating this App so its legacy HTTP
source can migrate only after verified HTTPS validates successfully.

The App uses its own `/data/gateway` private volume and must be upgraded in place to
retain private state, including its TLS trust identity.
