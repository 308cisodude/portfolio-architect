# Portfolio Architect 1.38.0

Portfolio Architect 1.38.0 is a native Home Assistant dashboard-usability milestone built on the live-accepted v1.37.0 runtime. It collects two concrete presentation improvements observed during live use without changing provider acquisition, portfolio calculation, execution/funding semantics or Gateway wire contracts.

## Copy-friendly recommended-purchase ISIN

Recommended purchases remain dynamic presentation-slot rows and the dashboard still contains no hard-coded target IDs, ISIN-derived holding IDs or sample-instrument inventory. A visible recommended-purchase amount now has native interactions:

- **tap:** open the corresponding generic presentation-slot ISIN entity, exposing a copy-friendly ISIN state;
- **hold:** open the corresponding bounded purchase-explanation entity.

Only rows with a positive proposed buy remain visible. The presentation-slot mapping is still ephemeral UI projection; stable target identity remains the opaque `target_id` repeated in slot attributes.

## Policy-aware investment-cash context

The native **Authorized investment cash** Tile now shows its monetary state together with bounded context derived from already validated cash evidence:

- total available/eligible investment cash;
- cash excluded by the active authorization policy.

The **Cash after recommended purchases** Tile shows the same context plus planned cash outlay. With complete evidence, the displayed values therefore reconcile as:

`remaining cash + policy-excluded cash + planned cash outlay = total available cash`.

For `all_available`, the policy-excluded amount is zero. For `retain`, it is the actually excluded portion of the retained reserve. For `capped`, it is the difference between eligible cash and the actually authorized amount rather than mislabelling that difference as the configured cap.

Provider-scoped eligible/authorized cash is summed only when every contributing provider exposes complete rich authorization metadata. If provider-scoped evidence is incomplete, the context fails closed instead of constructing a partial total. The established top-level eligible/authorized pair remains the compatibility fallback when no provider-scoped list exists.

English and German dashboard views use the same underlying numeric evidence with locale-appropriate display formatting.

## Preserved behavior and security boundaries

Historical experimental `v1.19.0-rc2` brokerage-diagnostic work remains excluded and is not promoted by this release.

- payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged; schemas 1–5 remain supported;
- presentation schema 2 and v1.36 bounded presentation-slot backend: unchanged;
- broker schemas 1/2/3 runtime compatibility: unchanged;
- provider-scoped authorized cash, retained-cash mathematics and exact directed funding topology: unchanged;
- v1.37 shared Gateway human-input validation and v1.35.4 Comdirect cash-input UX: unchanged;
- v1.35.1 Comdirect OAuth/session-maintenance resilience: unchanged;
- Trade Republic local/private statement import: unchanged; this release does not move PDF parsing into Portfolio Architect and no cash or transaction-history parser is added;
- DKB remains experimental, manual-only and non-live; DKB live Gateway acquisition remains a later authenticated milestone;
- private-PKI verified HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-plaintext fallback: unchanged;
- no trading, order placement, transfer execution, payment, transaction-history or automatic-sell capability is added.

No trading, order, transfer, payment, or transaction-history capability is introduced by v1.38.0.

The reference dashboard changes in this release. HACS does not overwrite user-owned Lovelace YAML, so users who want the v1.38.0 presentation must deliberately replace or merge their copied dashboard; bulk replacement with the supplied bilingual dashboard is the recommended upgrade path.

The v1.33.0 source-freshness and plan-schedule separation remains unchanged: recurring scheduling stays anchored to the latest valid Portfolio Architect evaluation, source timestamps remain evidence-only freshness inputs, and v1.38.0 does not change any configured freshness threshold.
