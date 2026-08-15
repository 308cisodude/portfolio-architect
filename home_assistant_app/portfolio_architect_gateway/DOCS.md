# Portfolio Architect Gateway — Comdirect v1.27.0

Version 1.27.0 serves the private Portfolio Architect REST/health API over
certificate-verified HTTPS. The App creates a persistent per-installation private
CA and Supervisor-hostname server certificate under `/data/gateway/tls`, keeps all
private keys App-local, and publishes only its public CA/fingerprint plus bounded
endpoint identity through Supervisor discovery. The existing bearer token remains
required.

Comdirect acquisition, OAuth/session, PhotoTAN, account selection, authorized cash,
REST schema 1 and health schema 6 are unchanged. Upgrade the Portfolio Architect
Home Assistant integration to 1.27.0 before updating this App so its legacy HTTP
source can migrate only after verified HTTPS validates successfully.

The App uses its own `/data/gateway` private volume and must be upgraded in place to
retain private state, including its TLS trust identity.
