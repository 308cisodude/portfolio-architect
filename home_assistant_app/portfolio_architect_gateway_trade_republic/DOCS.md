# Portfolio Architect Gateway — Trade Republic v1.25.0

Version 1.25.0 supports local import of the German text-PDF **DEPOTAUSZUG** statement family through this App's admin-only Ingress page.

The upload is bounded to 5 MiB, parsed locally in memory, and the original PDF is discarded. Only the validated provider-neutral holdings snapshot is stored in `/data/gateway`. Encrypted, scanned/image-only, unsupported, ambiguous, future-dated or internally inconsistent documents are rejected without replacing the last accepted snapshot.

After a successful import the authenticated private REST endpoint can serve the normalized holdings and health schema 6 reports `provider_id: trade_republic`. The bearer token shown on the Ingress page is private; do not publish screenshots containing it.

Portfolio Architect 1.25.0 still configures one primary REST Gateway plus supplemental CSV sources. Do not assume simultaneous Comdirect + Trade Republic REST aggregation from this release alone.
