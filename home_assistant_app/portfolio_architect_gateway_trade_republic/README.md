# Portfolio Architect Gateway — Trade Republic v1.26.6

The Trade Republic App remains an isolated statement-import provider. Use the admin-only Ingress page to import a current supported German text-PDF `DEPOTAUSZUG`. The PDF is processed in memory and discarded; only the normalized holdings snapshot and private bearer token persist.

The App exposes that accepted snapshot through the authenticated read-only REST schema used by other Portfolio Architect Gateways and remains configured for automatic startup. Version 1.26.6 does not change statement parsing or the Gateway wire contract; it only aligns the App package with Portfolio Architect's Home Assistant-side unavailable-source diagnostics hotfix. The v1.26.1 ISIN-first identity behavior remains unchanged.

The App uses its own `/data/gateway` private volume and must be upgraded in place to retain private state.
