# Portfolio Architect 1.38.1

Portfolio Architect 1.38.1 is a narrow native-dashboard follow-up to the published v1.38.0 release. The richer per-target drift visualization discussed while v1.38.0 was prepared was not included in the published v1.38.0 dashboard; v1.38.1 adds that presentation cleanly on top of the immutable published baseline without changing portfolio calculations, provider acquisition, execution/funding semantics or Gateway wire contracts.

## Dynamic native allocation drift

The reference dashboard now consumes the existing bounded target presentation slots as dynamic signed drift Tiles. For each of the 32 generic target slots, three native Home Assistant Conditional variants select the visible presentation from the slot's allocation status:

- **underweight:** amber;
- **on target:** green;
- **overweight:** red.

Each visible card is a core Tile bound to the slot's numeric allocation-drift sensor. The Tile uses the entity's dynamic instrument name and the native `bar-gauge` feature with a fixed signed range of **-100 to +100 percentage points**, so positive and negative drift share one stable scale without instrument-specific YAML. Tapping the drift Tile opens the same slot's bounded allocation-explanation entity. Unused trailing slots remain unavailable and are naturally suppressed by the state conditions.

A separate synthetic target marker is not included. The dashboard presents the signed percentage-point drift that Portfolio Architect already calculates and exposes; it does not fabricate a second frontend calculation or custom-card state.

The implementation remains bounded and native-only. It adds no `auto-entities`, card-mod, JavaScript, custom frontend dependency, target hash, holding ID or sample instrument inventory to the dashboard. The presentation-slot mapping remains an ephemeral UI projection; stable target identity remains the opaque `target_id` repeated in slot attributes.

## v1.38.0 usability work preserved

The published v1.38.0 presentation improvements remain unchanged:

- a visible recommended-purchase row still opens the matching generic presentation-slot ISIN entity on tap and the bounded purchase explanation on hold;
- **Authorized investment cash** still shows total available cash plus cash excluded by policy when complete validated evidence exists;
- **Cash after recommended purchases** still shows the same policy context plus planned cash outlay;
- incomplete provider-scoped cash evidence still fails closed rather than constructing a partial total.

English and German dashboard views use the same underlying entities and bounded candidate ranges.

## Preserved behavior and security boundaries

Historical experimental `v1.19.0-rc2` brokerage-diagnostic work remains excluded and is not promoted by this release.

- payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged; schemas 1–5 remain supported;
- presentation schema 2 and the v1.36 bounded presentation-slot backend: unchanged;
- broker schemas 1/2/3 runtime compatibility: unchanged;
- provider-scoped authorized cash, retained-cash mathematics and exact directed funding topology: unchanged;
- v1.37 shared Gateway human-input validation and v1.35.4 Comdirect cash-input UX: unchanged;
- v1.35.1 Comdirect OAuth/session-maintenance resilience: unchanged;
- Trade Republic local/private statement import: unchanged; this release does not move PDF parsing into Portfolio Architect and no cash or transaction-history parser is added;
- DKB remains experimental, manual-only and non-live; DKB live Gateway acquisition remains a later authenticated milestone;
- private-PKI verified HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-plaintext fallback: unchanged;
- no trading, order placement, transfer execution, payment, transaction-history or automatic-sell capability is added.

No trading, order, transfer, payment, or transaction-history capability is introduced by v1.38.1.

The reference dashboard changes in this release. HACS does not overwrite user-owned Lovelace YAML, so users who want the v1.38.1 drift presentation must deliberately replace or merge their copied dashboard; bulk replacement with the supplied bilingual dashboard is the recommended upgrade path.

The v1.33.0 source-freshness and plan-schedule separation remains unchanged: recurring scheduling stays anchored to the latest valid Portfolio Architect evaluation, source timestamps remain evidence-only freshness inputs, and v1.38.1 does not change any configured freshness threshold.
