# Portfolio Architect 1.36.0

Portfolio Architect 1.36.0 completes the native dynamic portfolio-presentation milestone. The v1.34 structural presentation model is now consumed through bounded diagnostic presentation-slot adapter entities, allowing the supplied English/German reference dashboard to show the actual current target architecture, complete outside-current-plan inventory and active policy findings without maintaining instrument-specific YAML lists.

## Native dynamic presentation

The canonical stable entities are unchanged. Opaque target-ID entities remain the identity contract for configured target roles; accepted holding `position_id` entities remain the identity contract for current holdings. v1.36.0 adds predictable generic presentation aliases such as `presentation_target_01_current_allocation` and `presentation_outside_001_holding_value` solely as an ephemeral UI projection. Every available slot repeats the underlying stable identity in attributes.

`sensor.portfolio_architect_presentation_model` advances from presentation schema 1 to schema 2. Target and outside-scope rows now include one-based `presentation_slot` and `slot_key` metadata, and the model adds a bounded active-policy-finding slot index. The accepted portfolio payload remains schema 8; this is a Home Assistant presentation contract only.

The dashboard candidate ranges exactly match backend bounds: 32 target slots, 512 outside-holding slots and 256 policy-finding slots. Slot entities are created only as current accepted data requires them; stale slots become unavailable when their current mapping disappears. They deliberately have no measurement state class, because slot numbers are not long-term instrument identity.

## Native dashboard only

The v1.36.0 reference dashboard uses core Home Assistant `entity-filter` cards to filter generic bounded candidates and pass current entities to native Entities, Glance and Distribution cards. Existing Tile and Conditional cards remain for static aggregate/runtime presentation. There is no `auto-entities`, card-mod, custom JavaScript or custom-card dependency.

The dashboard no longer contains hard-coded opaque target IDs, ISIN-derived holding IDs or sample-instrument names for portfolio inventory. Native more-info interaction remains available on the filtered entities.

The supplied dashboard is still a reference artifact, not integration-owned configuration. HACS never overwrites a user's imported or customized Lovelace dashboard. Users who want the v1.36.0 dynamic presentation must deliberately replace/update their copied dashboard YAML.

## Preserved contracts

- payload schema 8: unchanged.
- REST portfolio schema 1: unchanged.
- Gateway health schema 6: unchanged; schemas 1–5 remain supported.
- Broker schemas 1/2/3 remain runtime-compatible.

Historical experimental `v1.19.0-rc2` brokerage-diagnostic work remains excluded and is not promoted by this release. The v1.33.0 source-freshness and plan-schedule separation remains unchanged: the plan schedule is anchored to the latest valid Portfolio Architect evaluation and this release does not change any configured freshness threshold. No trading, order, transfer, payment, or transaction-history capability is added.

## Preserved behavior

Provider acquisition and security are unchanged. DKB live Gateway acquisition remains a later authenticated milestone. Comdirect retains v1.35.1 session-maintenance resilience and v1.35.4 locale-tolerant cash-policy input; Trade Republic statement import remains private/local and this release does not move PDF parsing into Portfolio Architect; DKB remains experimental, manual-only and non-live. Provider-scoped authorized cash, retained reserves, exact directed funding topology, broker schemas 1/2/3, private-PKI verified HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-plaintext fallback are unchanged.

Portfolio Architect remains advisory software: no trading, order placement, transfer execution, payment, transaction-history or automatic-sell capability is added.
