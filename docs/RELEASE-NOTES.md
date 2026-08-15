# Portfolio Architect 1.26.7

Version 1.26.7 is a narrow common-Gateway integrity hotfix discovered during the
v1.26.6 overnight live-acceptance test. After a long Comdirect Gateway stop, the
Gateway correctly entered reauthentication-required / last-known-good operation,
and v1.26.6 correctly identified **Comdirect Gateway** as unavailable. Portfolio
Architect's fail-closed integrity layer then detected a second issue: a `304 Not
Modified` response reported a different snapshot fingerprint.

## Persisted quantity is preserved

REST schema 1 already supports an optional canonical position `quantity`. Live
provider snapshots wrote that field to the private cached snapshot, but the common
Gateway cache parser did not restore it after restart. Reloading an unchanged
quantity-bearing snapshot could therefore change its JSON body, SHA-256 and ETag
while retaining the same `generated_at` timestamp.

Version 1.26.7 parses and restores optional quantity through the same bounded
canonical-decimal path used by the existing snapshot contract. Save/load of an
unchanged quantity-bearing snapshot is now byte-for-byte stable, including its
SHA-256 and ETag.

## Correct HTTP conditional-validator precedence

The Gateway previously evaluated `If-Modified-Since` even when an
`If-None-Match` header was present but did not match the current ETag. In the cold
restart edge case, the unchanged timestamp could therefore produce `304 Not
Modified` even though the representation fingerprint had changed.

Version 1.26.7 gives ETag validation precedence. When `If-None-Match` is present:

- a matching ETag may return `304 Not Modified`;
- a non-matching ETag returns the current representation with `200 OK`; and
- `If-Modified-Since` is not consulted.

The date validator remains available when no ETag validator is supplied.

## Integrity enforcement remains fail-closed

Portfolio Architect's snapshot-integrity checks are unchanged. The v1.26.6 live
system correctly rejected the inconsistent evidence and retained the previously
accepted snapshot rather than silently trusting a contradictory `304` response.
This release repairs the Gateway behavior that triggered that protection; it does
not weaken the protection itself.

## Compatibility

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported
- existing Home Assistant entity IDs / unique IDs: unchanged
- v1.26.6 unavailable-source diagnostics: unchanged
- v1.26.5 authoritative DATE sensors and read-only `date.*` presentation mirrors:
  unchanged
- Comdirect OAuth/session, PhotoTAN, refresh cadence, account selection and
  authorized-cash semantics: unchanged
- Trade Republic statement import and persisted-snapshot contract: unchanged
- DKB Gateway: still experimental/manual-only/fail-closed, no acquisition path
- no trading/order/transfer/payment/transaction-history capability

Gateway HTTPS transport hardening remains the next security milestone in v1.27.0.

## Historical boundaries

DKB live Gateway acquisition remains a later provider-specific milestone. Trade
Republic statement parsing remains isolated in its provider App; this release
does not move PDF parsing into Portfolio Architect. The historical
experimental `v1.19.0-rc2` brokerage diagnostics/fee-probe work remains separate
and is not promoted by this release.

No trading, order, transfer, payment, or transaction-history capability is added by
this release.
