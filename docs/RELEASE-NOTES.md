# Portfolio Architect 1.26.6

Version 1.26.6 is a narrow source-diagnostics hotfix after v1.26.5 live acceptance.
During a Comdirect PhotoTAN reauthentication event, the primary Gateway remained
reachable and continued serving its trusted cached snapshot, so Portfolio Architect
gracefully degraded and disabled new investment actionability as designed. The
**Source unavailable** Tile nevertheless rendered `None` instead of identifying
**Comdirect Gateway**.

## Non-live Gateway source identification

The unavailable-source metadata no longer depends on Portfolio Architect having
activated its separate Home Assistant last-known-good cache before the primary REST
Gateway can be named.

A configured REST Gateway is now included in the bounded unavailable-source set
whenever its observed Gateway operating mode is not `live`. This covers, among other
states:

- `reauthentication_required` while the Gateway still serves its own trusted cached
  snapshot;
- `last_known_good` Gateway-local cached operation; and
- an unreachable/unavailable primary Gateway when Portfolio Architect falls back to
  its Home Assistant LKG.

The same rule is applied symmetrically to additional REST Gateways whose health is
available but non-live. Existing supplemental transport/authentication/integrity
error collection and DKB CSV source diagnostics remain unchanged.

The public labels continue to be derived only from bounded provider/source IDs. No
endpoint URL, bearer token, account identifier, file path, or provider-private state
is exposed.

## No Comdirect authentication change

Version 1.26.6 does not alter Comdirect OAuth/session persistence, PhotoTAN handling,
refresh cadence, account selection, authorized investment cash, Gateway shutdown,
or provider acquisition. A short controlled stop/start test during v1.26.5 live
acceptance confirmed that normal App restarts preserve the persisted Comdirect
session state; the diagnostic defect was independent of that behavior.

## Compatibility

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported
- existing Home Assistant entity IDs / unique IDs: unchanged
- v1.26.5 authoritative DATE sensors and read-only native `date.*` presentation
  counterparts: unchanged
- provider acquisition/authentication/private state: unchanged
- Comdirect authorized-cash semantics: unchanged
- Trade Republic statement import/persisted snapshot: unchanged
- DKB Gateway: still experimental/manual-only/fail-closed, no acquisition path
- no trading/order/transfer/payment/transaction-history capability

Gateway HTTPS transport hardening remains the next security milestone in v1.27.0.

## Historical boundaries

DKB live Gateway acquisition remains a later provider-specific milestone; v1.26.6
does not promote the experimental DKB shell into a live acquisition source. Trade
Republic statement parsing remains isolated in the Trade Republic Gateway App; this
release does not move PDF parsing into Portfolio Architect.

The historical experimental `v1.19.0-rc2` brokerage diagnostics/fee-probe work
remains separate and is not promoted by this release.

No trading, order, transfer, payment, or transaction-history capability is added by
this release.
