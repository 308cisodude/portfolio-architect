# Portfolio Architect Gateway — Trade Republic v1.26.0

Version 1.26.0 retains the supported local import of the German text-PDF
**DEPOTAUSZUG** statement family through this App's admin-only Ingress page.

The upload is bounded to 5 MiB, parsed locally in memory, and the original PDF is
discarded. Only the validated provider-neutral holdings snapshot is stored in
`/data/gateway`. Encrypted, scanned/image-only, unsupported, ambiguous,
future-dated or internally inconsistent documents are rejected without replacing
the last accepted snapshot.

After a successful import the authenticated private REST endpoint serves the
normalized holdings through REST schema 1 and health schema 6 reports
`provider_id: trade_republic`. The bearer token shown on the Ingress page is
private; do not publish screenshots containing it.

The App now starts automatically because Portfolio Architect 1.26.0 can keep this
Gateway configured as an additional REST source alongside another primary Gateway.
Its acquisition mechanism remains the explicit local statement import; automatic
App startup does not imply automatic broker acquisition.
