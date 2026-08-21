# Portfolio Architect 1.41.0

Portfolio Architect v1.41.0 adds **strict local Trade Republic cash-statement acquisition** without introducing an unofficial Trade Republic API, transaction-history ingestion, or any money-movement capability. The Trade Republic Gateway now treats the established German text-PDF `DEPOTAUSZUG` holdings family and the German text-PDF `KONTOAUSZUG` cash family as independent evidence sources.

## Trade Republic cash statements

The admin-only Trade Republic Gateway Ingress UI now exposes two separate import paths:

- `DEPOTAUSZUG` → validated holdings snapshot;
- `KONTOAUSZUG` → validated provider-scoped cash snapshot.

The cash parser is deliberately bounded and fail-closed. It validates the Trade Republic issuer marker, one unambiguous `Cashkonto` summary, beginning balance + incoming payments − outgoing payments = ending balance, one unambiguous `BARMITTELÜBERSICHT` as-of date, and reconciliation of trust-account plus qualified money-market-fund components against the ending cash balance. Unsupported, encrypted, image-only, malformed, ambiguous, future-dated, or internally inconsistent documents are rejected without replacing either last accepted private snapshot.

Uploaded PDFs are parsed in memory and are never persisted. Transaction rows, transfer counterparties, IBAN/account identifiers, account holder/address data, and raw statement text are not retained. Only a schema-1 private cash state containing the bounded EUR balance plus evidence timestamps is stored in the Trade Republic App-private data volume.

## Independent holdings and cash evidence

Trade Republic holdings and cash are now stored independently and composed only at the provider-neutral REST boundary. Importing fresh cash does not refresh the holdings timestamp, and importing fresh holdings does not refresh the cash timestamp. A failed cash import cannot replace accepted holdings; a failed depot import cannot erase accepted cash.

REST portfolio schema 1 is unchanged. The existing additive `investment_reserve` and `investment_cash` fields carry the accepted Trade Republic cash result. Home Assistant now permits those cash timestamps to be independent of the holdings snapshot timestamp and separately freshness-gates provider cash using the configured `imported_statement` evidence threshold before it can affect funding decisions. Stale cash is silently excluded from route funding while still-valid holdings remain usable according to their own freshness evidence.

## Security and provider boundaries

- No Trade Republic credentials are requested or stored.
- No private/undocumented Trade Republic API is contacted.
- No transaction-history model or transaction rows are persisted.
- No trading, order placement/cancellation, transfer, payment, sell, or withdrawal capability is added.
- Verified private-PKI HTTPS, bearer authentication, provider isolation, REST schema 1, Gateway health schema 6, broker schemas 1/2/3, and the advisory-only execution boundary remain intact.
- The DKB anonymous FinTS capability probe and Comdirect live acquisition behavior are unchanged apart from normal 1.41.0 package/version alignment.

## Presentation

The v1.39.0 colourful paired allocation Tiles and v1.38.1 signed drift presentation are unchanged. The v1.41.0 bilingual reference dashboard is byte-identical to v1.40.1, so no dashboard YAML migration is required.

## Upgrade intent

After updating the integration and Gateway Apps in place, open **Portfolio Architect Gateway — Trade Republic** and import a current official `KONTOAUSZUG` through the new cash-statement form. Keep the existing `DEPOTAUSZUG` import for holdings. The two imports are intentionally separate so each evidence family can age and fail closed independently.

## Compatibility contracts retained

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported.
- presentation schema 2 remains unchanged.
- broker schemas 1/2/3 remain unchanged.
- The v1.33.0 source-freshness and plan-schedule separation remains unchanged: recurring scheduling stays anchored to the latest valid Portfolio Architect evaluation, and v1.41.0 does not change any configured freshness threshold.
- DKB live Gateway acquisition remains a later gated milestone; this release does not infer authenticated holdings support from anonymous capability evidence.
- Trade Republic PDF parsing remains inside its provider-isolated Gateway App and does not move PDF parsing into Portfolio Architect.
- The historical v1.19.0-rc2 state remains historical and is not promoted by this release.
- The colourful paired allocation Tile view was not included in v1.38.1; it arrived in v1.39.0 and remains unchanged here.
- No trading, order, transfer, payment, or transaction-history capability is introduced by v1.41.0.
