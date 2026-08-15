# Portfolio Architect Gateway — Trade Republic v1.26.7

The Trade Republic App remains an isolated statement-import provider. Use the admin-only Ingress page to import a current supported German text-PDF `DEPOTAUSZUG`; the PDF is processed in memory and discarded, while only the normalized holdings snapshot and private bearer token persist.

Version 1.26.7 changes only the common Gateway cached-snapshot/HTTP validator layer: optional quantity survives reload and ETag validation has correct precedence. Statement parsing, provider acquisition model, REST schema 1 and health schema 6 are unchanged.

The App uses its own `/data/gateway` private volume and must be upgraded in place to retain private state.
