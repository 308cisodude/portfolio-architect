# Portfolio Architect Gateway — Trade Republic v1.26.1

The Trade Republic App remains an isolated statement-import provider. Use the admin-only Ingress page to import a current supported German text-PDF `DEPOTAUSZUG`. The PDF is processed in memory and discarded; only the normalized holdings snapshot and private bearer token persist.

The App exposes that accepted snapshot through the authenticated read-only REST schema used by other Portfolio Architect Gateways and remains configured for automatic startup. Version 1.26.1 does not change statement parsing or the Gateway wire contract; Portfolio Architect now correctly treats the App's ISIN-only holdings as ISIN-primary identities instead of requiring a WKN.

The App uses its own `/data/gateway` private volume and must be upgraded in place to retain private state.
