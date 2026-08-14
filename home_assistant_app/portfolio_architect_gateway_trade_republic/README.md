# Portfolio Architect Gateway — Trade Republic v1.26.0

The Trade Republic App is an isolated statement-import provider. Use the admin-only
Ingress page to import a current supported German text-PDF `DEPOTAUSZUG`. The PDF
is processed in memory and discarded; only the normalized holdings snapshot and
private bearer token persist.

The App exposes that accepted snapshot through the same authenticated read-only
REST schema used by other Portfolio Architect Gateways. Version 1.26.0 changes the
App to automatic startup so it can remain an ongoing Portfolio Architect REST
source across Home Assistant restarts. It does not automatically acquire data from
Trade Republic; refreshing holdings still requires an explicit supported statement
import.

The App uses its own `/data/gateway` private volume and must be upgraded in place to
retain private state.
