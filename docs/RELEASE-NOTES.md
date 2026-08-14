# Portfolio Architect 1.26.0

Version 1.26.0 adds simultaneous aggregation of multiple independent Portfolio
Architect Gateway REST sources. Provider-specific acquisition remains isolated in
each Gateway App: Comdirect can continue to acquire holdings from the broker API,
Trade Republic can continue to acquire holdings from a private `DEPOTAUSZUG` PDF,
and Portfolio Architect consumes only their common provider-neutral REST snapshot
contract.

## Multiple Gateway REST sources

An existing REST installation keeps its current Gateway as the primary source.
Additional local Gateways can be added or removed under **Portfolio sources →
Additional REST Gateways** without reconfiguring the primary source.

Before an additional Gateway is saved, Portfolio Architect validates:

- a bounded local-only HTTP(S) endpoint;
- bearer authentication;
- Gateway health schema 6 with a stable bounded `provider_id`;
- a healthy/live snapshot;
- REST snapshot position-count and fingerprint integrity metadata; and
- consistency between the health document and the returned snapshot.

Additional Gateway bearer tokens remain only in the private Home Assistant config
entry options. Diagnostics expose provider identity and bounded health state, never
tokens.

## Atomic aggregation and graceful degradation

All configured sources are normalized into the existing `PortfolioSourceSnapshot`
model and merged by the established provider-neutral aggregation engine. A refresh
is atomic: Portfolio Architect does not silently drop a configured provider and
recalculate a smaller portfolio when one additional Gateway is unavailable,
unauthorized, inconsistent, or attempts to move backwards in snapshot time.

If a previously validated complete aggregate exists, such a failure retains that
complete Home Assistant last-known-good calculation. Runtime health becomes
degraded/last-known-good and new investment actionability is disabled until every
configured REST Gateway is healthy again. If no matching complete last-known-good
aggregate exists, the update fails closed.

The configured source set participates in the private LKG configuration fingerprint,
so adding or removing a Gateway cannot replay a cache that was built from a
different provider set.

## Distinct providers and provenance

Source instances and provider identities are now deliberately separate concepts.
The aggregate summary retains `source_count` and adds bounded `provider_count` and
`provider_ids` metadata. Two DKB CSV files therefore remain two sources but one
provider.

Per-position source provenance is unchanged and continues to show which independent
sources contributed to an aggregated holding. The reference dashboard's **Source
provider** tile now renders a compact distinct-provider summary, for example:

`Multi-source portfolio · 3 providers`

Copied/imported reference dashboards remain user-owned and are not overwritten by
HACS; this visual change must be deliberately applied to an existing copied
dashboard.

## Trade Republic runtime

The accepted v1.25.0 Trade Republic statement importer is unchanged. Its App now
uses `boot: auto` so an accepted snapshot can remain available to a configured
Portfolio Architect REST consumer across Home Assistant restarts. Before its first
accepted statement it still fails closed with no fabricated portfolio.

The original Trade Republic PDF remains transient private input and is never
persisted. The provider-specific parser and hash-locked `pypdf` dependency remain
confined to the Trade Republic App.

## Compatibility and safety

- payload schema 8 (unchanged)
- REST portfolio schema 1 (unchanged)
- Gateway health schema 6 (unchanged; schemas 1–5 remain supported for a single primary Gateway)
- Existing Home Assistant entity IDs / unique IDs: unchanged
- Existing primary Comdirect endpoint/token and private Gateway state: unchanged
- Comdirect cash authorization remains authoritative for the existing investment-cash path
- DKB supplemental CSV behavior: unchanged
- v1.20/v1.20.1 LKG semantics: retained and extended atomically across the configured REST source set
- v1.21 actionability semantics: retained
- v1.22 publication/privacy gates: retained
- No trading, order, transfer, payment, or transaction-history capability

## Historical boundaries

Version 1.25.0 introduced the supported Trade Republic holdings-statement importer.
Version 1.26.0 does not move PDF parsing into Portfolio Architect; it only teaches
the Home Assistant integration to consume more than one already-normalized Gateway
REST snapshot at the same time. DKB live Gateway acquisition remains a later
provider-specific milestone.
The historical `v1.19.0-rc2` brokerage-diagnostics/fee-probe branch remains separate
and is not promoted by this release. Multi-Gateway aggregation consumes only the
established holdings snapshot contract and does not reintroduce those experimental
brokerage diagnostics.
