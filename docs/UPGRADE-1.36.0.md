# Upgrade to Portfolio Architect 1.36.0

Version 1.36.0 completes the native dynamic portfolio-presentation milestone that began with the
v1.34 structural presentation contract. The integration now exposes bounded presentation-slot
adapter entities whose predictable IDs let the reference Lovelace dashboard render the current
configured target architecture, current outside-scope inventory and active policy findings without
instrument-specific YAML lists or custom frontend dependencies.

## Recommended upgrade order

1. Update **Portfolio Architect** through HACS to **1.36.0** and restart Home Assistant once.
2. Confirm the integration remains healthy/live and the existing target, holding, policy, execution,
   provider-cash and funding entities remain available with their established stable IDs.
3. Update all installed Portfolio Architect Gateway Apps to **1.36.0** in place. No provider runtime
   semantics change in this release; do not clear App-private data or reauthenticate solely for the
   upgrade.
4. If you use the supplied reference dashboard, deliberately replace your copied dashboard YAML with
   the v1.36.0 bilingual reference YAML. HACS never overwrites a user-owned Lovelace dashboard.
5. Confirm target counts, outside-scope counts and active policy findings reconcile with the visible
   dynamic dashboard inventory.

## Presentation schema 2

`sensor.portfolio_architect_presentation_model` now reports presentation schema 2. Stable portfolio
identity is unchanged: target rows remain keyed by opaque `target_id`, and outside holdings remain
keyed by their accepted `position_id`. Schema 2 adds one-based bounded `presentation_slot`/`slot_key`
metadata and an active-policy-finding slot index so the native dashboard projection can be audited
against the same authoritative current-state ordering.

The slot entities are deliberately **not** stable portfolio identities. They are diagnostic UI
projections such as `presentation_target_01_current_allocation` and
`presentation_outside_001_holding_value`. If the configured/current inventory changes, a slot can map
to a different stable target or holding. Every available slot therefore repeats its stable identity
in attributes. Automations and long-term identity/history should continue to use the existing
stable target-ID and position-ID entities, not presentation slots.

## Native dashboard behavior

The v1.36.0 reference dashboard uses only Home Assistant core cards. Native `entity-filter` cards
filter the bounded candidate slot ranges and feed the resulting current entities into normal native
Entities, Glance and Distribution cards. There is no `auto-entities`, card-mod, custom JavaScript or
custom-card dependency. Missing/unavailable candidate slots do not become visible inventory.

The supported bounds remain unchanged: at most 32 configured target positions, at most 512 accepted
holdings, and at most 256 policy findings. The dashboard candidate ranges match those backend bounds,
so the visible inventory cannot silently truncate an accepted current portfolio.

## Preserved contracts

- portfolio payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged;
- broker schemas 1/2/3 runtime compatibility: unchanged;
- provider-scoped cash, exact directed funding topology and retained-cash authorization: unchanged;
- Comdirect OAuth/session/PhotoTAN and v1.35.1 maintenance resilience: unchanged;
- v1.35.4 locale-tolerant Comdirect cash-policy input: unchanged;
- Trade Republic statement import/private diagnostics: unchanged;
- DKB remains experimental, manual-only and non-live;
- private-PKI verified HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and
  no-plaintext fallback: unchanged;
- no trading, order placement, transfer execution, payment, transaction-history or automatic-sell
  capability is added.

## Rollback

The underlying stable target/holding entities and wire schemas are unchanged, so an integration
rollback does not require portfolio or Gateway data migration. A v1.35.x reference dashboard does
not understand the v1.36 presentation slots and remains a static sample inventory. Restore the older
reference dashboard as well if deliberately rolling the presentation layer back.
