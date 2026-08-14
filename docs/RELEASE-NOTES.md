# Portfolio Architect 1.25.0

Version 1.25.0 adds local Trade Republic statement import inside the separate
**Portfolio Architect Gateway — Trade Republic** App. The existing Comdirect
runtime, DKB shell, portfolio calculations, wire schemas and Home Assistant entity
semantics remain unchanged.

## Supported Trade Republic statement family

The Trade Republic App now accepts the German text-PDF **DEPOTAUSZUG** statement
family through its admin-only Ingress page. The importer is deliberately narrow:

- the PDF must be unencrypted and contain an extractable text layer;
- the document must identify itself as a Trade Republic `DEPOTAUSZUG`;
- statement date and document creation date must be unambiguous and match;
- each supported position must contain a quantity, EUR market value and exactly one
  ISIN;
- the parsed number of positions and summed EUR market value must exactly match the
  document summary; and
- unsupported, scanned/image-only, ambiguous or internally inconsistent documents
  fail closed without replacing the last accepted snapshot.

The supported document is a holdings snapshot only. No transaction history is
parsed or exposed.

## Private local import

Uploaded PDFs are bounded to 5 MiB and parsed in memory. The original document is
not written to App storage. Only the existing provider-neutral REST-schema-1
`PortfolioSnapshot` is atomically persisted under the Trade Republic App's private
`/data/gateway` volume. Account-holder data, postal addresses, depot/account
identifiers, tax information and other attribution fields are ignored by the
parser and do not enter the REST payload, health response or logs.

The upload route remains behind Supervisor Ingress and adds a per-process CSRF
nonce. Import failures produce bounded generic reasons and never echo document
text, filenames, holdings values or identifiers into logs.

## Provider-specific PDF dependency

Only the Trade Republic App installs `pypdf 6.15.0`, locked to the reviewed
pure-Python wheel SHA-256. Comdirect, DKB and the standalone Gateway remain free of
that provider-specific parser and dependency. Protected CI builds and starts all
provider App containers before publication.

## Runtime semantics

Before the first accepted statement, the Trade Republic App remains intentionally
degraded/unavailable with no snapshot. After a successful import, its provider
returns the normalized snapshot through the unchanged authenticated GET-only REST
service and health schema 6 reports `provider_id: trade_republic`.

Portfolio Architect still supports one configured primary REST Gateway plus its
established supplemental CSV model. Consuming Comdirect and Trade Republic as two
simultaneous REST Gateways is not introduced by this release.

## Compatibility and safety

- payload schema 8 (unchanged)
- REST portfolio schema 1 (unchanged)
- Gateway health schema 6 (unchanged; schemas 1–5 remain supported)
- Existing Home Assistant entity IDs / unique IDs: unchanged
- Comdirect credentials/session, selected account and cash policy: unchanged
- v1.20/v1.20.1 LKG semantics: unchanged
- v1.21 actionability semantics: unchanged
- v1.22 publication/privacy gates: retained
- Dashboard: unchanged
- No trading, order, transfer, payment, or transaction-history capability

## Historical experimental branch boundary

No DKB or Trade Republic acquisition runtime is shipped by v1.24.1. Version 1.25.0
adds the first supported Trade Republic acquisition path, limited to local holdings-statement import.

The historical `v1.19.0-rc2` brokerage-diagnostics branch remains separate and is not promoted by this release. The Trade Republic importer is holdings-only and does not reintroduce brokerage diagnostics or transaction/order capabilities.
