# Portfolio Architect Gateway — Trade Republic v1.27.3

Version 1.27.3 is package alignment for the Portfolio Architect DKB discovery-identity hotfix; Trade Republic statement import, persisted snapshot behavior, TLS trust and bearer authentication are unchanged from v1.27.2.

Version 1.27.3 is package alignment for the Home Assistant-side discovery-flow
hotfix and continues to serve that snapshot over the same certificate-verified
HTTPS Gateway boundary as v1.27.1. A persistent App-private CA/server certificate protects the
private REST transport and only public trust plus bounded endpoint identity is
published through Supervisor discovery. The bearer token remains required.

Statement parsing, persisted snapshot semantics, REST schema 1 and health schema 6
are unchanged. The App uses its own `/data/gateway` private volume and must be
upgraded in place to retain private state, including its TLS trust identity.
