# Portfolio Architect Gateway — Trade Republic v1.26.3

Version 1.26.3 retains the supported local import of the German text-PDF **DEPOTAUSZUG** statement family unchanged while aligning the App package with Portfolio Architect's Home Assistant-side dashboard/presentation follow-up.

The upload is bounded to 5 MiB, parsed locally in memory, and the original PDF is discarded. Only the validated provider-neutral holdings snapshot is stored in `/data/gateway`. Encrypted, scanned/image-only, unsupported, ambiguous, future-dated or internally inconsistent documents are rejected without replacing the last accepted snapshot.

After a successful import the authenticated private REST endpoint serves the normalized holdings through REST schema 1 and health schema 6 reports `provider_id: trade_republic`. The bearer token shown on the Ingress page is private; do not publish screenshots containing it.

The App starts automatically so Portfolio Architect can keep this Gateway configured as an additional REST source. Acquisition remains the explicit local statement import. The v1.26.1 ISIN-first downstream identity behavior remains unchanged; v1.26.3 adds no statement-parser, acquisition or REST-contract change.
