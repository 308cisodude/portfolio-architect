# Portfolio Architect Gateway — Trade Republic v1.27.0

The Trade Republic App remains an isolated statement-import provider. Use the
admin-only Ingress page to import a current supported German text-PDF `DEPOTAUSZUG`;
the PDF is processed in memory and discarded, while only the validated
provider-neutral holdings snapshot and private bearer token persist.

Version 1.27.0 serves that snapshot over the common certificate-verified HTTPS
Gateway boundary. A persistent App-private CA/server certificate protects the
private REST transport and only public trust plus bounded endpoint identity is
published through Supervisor discovery. The bearer token remains required.

Statement parsing, persisted snapshot semantics, REST schema 1 and health schema 6
are unchanged. The App uses its own `/data/gateway` private volume and must be
upgraded in place to retain private state, including its TLS trust identity.
