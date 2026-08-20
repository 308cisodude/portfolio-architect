# Portfolio Architect 1.36.1

Portfolio Architect 1.36.1 is a narrow Home Assistant presentation hotfix for the v1.36.0 native dynamic portfolio milestone. Live acceptance proved that the bounded presentation-slot backend, dynamic target/outside/policy filtering and numeric allocation entities were healthy, but a nested native Distribution card remained empty after `entity-filter` updated its candidate list.

## Dynamic allocation hotfix

The three dynamic allocation surfaces now use native Entities child cards behind the same `entity-filter` candidates and `numeric_state > 0` selection:

- whole-portfolio allocation;
- current-plan allocation; and
- plan-target allocation.

The bounded inventories remain unchanged: 32 targets, 512 outside holdings and 256 active policy findings. Presentation schema 2, stable opaque target identity, holding `position_id` identity and ephemeral slot semantics are unchanged.

Dynamic presentation candidates now request Home Assistant's structured entity-only name. This removes the device prefix from compact list/glance labels without hard-coding instrument names or identities into dashboard YAML. Per-entity allocation-status conditions and native more-info interaction are preserved.

No `auto-entities`, card-mod, custom JavaScript or custom card is introduced.

## Preserved behavior and security boundaries

Historical experimental `v1.19.0-rc2` brokerage-diagnostic work remains excluded and is not promoted by this release.

- payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged; schemas 1–5 remain supported.
- broker schemas 1/2/3 runtime compatibility: unchanged;
- provider-scoped authorized cash, retained-cash policy and exact directed funding topology: unchanged;
- v1.35.4 locale-tolerant Comdirect cash-policy parser and bounded invalid-input UX: unchanged;
- v1.35.1 Comdirect session-maintenance resilience: unchanged;
- Trade Republic local/private statement import: unchanged; this release does not move PDF parsing into Portfolio Architect.
- DKB remains experimental, manual-only and non-live; DKB live Gateway acquisition remains a later authenticated milestone.
- verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-plaintext fallback: unchanged;
- No trading, order, transfer, payment, or transaction-history capability is added; no automatic-sell capability is added.

The v1.33.0 source-freshness and plan-schedule separation remains unchanged: the plan schedule is anchored to the latest valid Portfolio Architect evaluation and this release does not change any configured freshness threshold.

The broader cross-Gateway human-input validation helper remains a deliberate future milestone; v1.36.1 does not generalize or relocate the v1.35.4 Comdirect parser.

The dashboard remains a user-owned reference artifact. Existing imported dashboards are never overwritten by HACS; live acceptance of v1.36.1 should deliberately bulk-replace the copied dashboard YAML with the supplied v1.36.1 bilingual dashboard.
