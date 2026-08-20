# Portfolio Architect 1.39.0

Portfolio Architect 1.39.0 is a native-dashboard presentation release built on the live-accepted v1.38.1 bounded-slot architecture. The colourful paired current/target Tile view was not included in v1.38.1; that release stopped at the signed drift restoration. It restores a richer colourful current-versus-target allocation view without bringing back static instrument inventories, custom frontend code, or the live-broken entity-filter/Distribution composition. Portfolio calculations, provider acquisition, execution/funding semantics and Gateway wire contracts are unchanged.

## Dynamic colourful current and target allocation

The **Current plan allocation** and **Plan target allocation** surfaces now render each configured target through paired native Home Assistant Conditional + Tile cards. The dashboard still enumerates only the fixed 32 generic presentation slots; it contains no target IDs, ISINs, WKNs, holding IDs or sample instrument names.

For each slot:

- the current and target Tile use the entity's dynamic instrument name;
- both Tiles use the same deterministic slot colour, giving the position a consistent visual identity across the two allocation columns;
- both Tiles use the native `bar-gauge` feature on a fixed 0–100% scale;
- visibility is conditioned on the slot's **target allocation**, not its current allocation, so a configured target that is currently missing still renders as a 0% current Tile instead of disappearing;
- unused trailing presentation slots remain unavailable and are suppressed naturally;
- tapping a Tile opens native more-info for the corresponding allocation entity.

The colour mapping belongs only to the ephemeral presentation-slot order. It is not portfolio identity and is never persisted into plan semantics. Stable target identity remains the opaque `target_id` repeated in slot attributes.

## Drift semantics remain unchanged

The live-accepted v1.38.1 **Current portfolio allocation** drift presentation is intentionally preserved. Its colours remain semantic rather than identity-based:

- **underweight:** amber;
- **on target:** green;
- **overweight:** red.

The signed drift Tiles continue to use the native -100…+100 percentage-point bar gauge and open the matching bounded allocation explanation on tap. The v1.38.0 policy-aware cash context and copy-friendly recommendation ISIN interaction are also unchanged.

## Native-only and bounded architecture

The reference dashboard remains core-Home-Assistant-only. It adds no `auto-entities`, card-mod, JavaScript, custom card or frontend dependency. The implementation uses the established presentation schema 2 bounded adapters and deliberately avoids an O(N²) family of target-count-specific Distribution-card variants.

English and German views consume the same underlying entities and the same deterministic slot-colour mapping.

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

No trading, order, transfer, payment, or transaction-history capability is introduced by v1.39.0.

The reference dashboard changes in this release. HACS does not overwrite user-owned Lovelace YAML, so users who want the v1.39.0 colourful allocation presentation must deliberately replace or merge their copied dashboard; bulk replacement with the supplied bilingual dashboard is the recommended upgrade path.

The v1.33.0 source-freshness and plan-schedule separation remains unchanged: recurring scheduling stays anchored to the latest valid Portfolio Architect evaluation, source timestamps remain evidence-only freshness inputs, and v1.39.0 does not change any configured freshness threshold.
