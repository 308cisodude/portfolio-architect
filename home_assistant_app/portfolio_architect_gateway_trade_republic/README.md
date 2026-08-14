# Portfolio Architect Gateway — Trade Republic v1.25.0

Version 1.25.0 turns the separate Trade Republic App into a manual statement-import provider. Use the admin-only Ingress page to import a current supported German text-PDF `DEPOTAUSZUG`. The PDF is processed in memory and discarded; only the normalized holdings snapshot and private bearer token persist.

The App uses its own `/data/gateway` private volume and must be upgraded in place to retain private state.
