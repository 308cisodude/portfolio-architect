# Portfolio Architect 1.35.2

Version 1.35.2 completes the v1.35 provider-scoped funding line with native execution-policy
configuration, explicit route-metadata semantics, and a retained-cash authorization option. It is
prepared on top of the published and live-accepted v1.35.1 baseline.

## Native execution-provider and funding editor

Home Assistant **Portfolio Architect → Configure → Execution providers & funding** can now edit an
existing provider-aware `broker.yaml` using validated native forms. The file remains the authoritative
runtime representation and direct YAML editing remains an advanced path.

The editor supports broker schemas 2 and 3 and can manage:

- the common fee-evidence freshness window;
- execution providers and their evidence source/date;
- explicit per-provider savings-plan eligibility, fee and promotional metadata; and
- exact directed funding-transfer edges with fee and conservative settlement business days.

Every save validates the complete broker document and atomically replaces `broker.yaml`. Schema 1
remains runtime-compatible but is not silently migrated by the native editor. Adding the first
funding edge deliberately upgrades schema 2 to schema 3; the reverse edge is never inferred.

## Cost-first route semantics made explicit

Execution economics are unchanged: actual execution and funding-transfer cost is primary, settlement
time is secondary for otherwise equivalent funded routes, and optional provider `priority` is only a
deterministic tie-break after those criteria. The native UI presents that field as **Tie-break
preference** and offers a neutral/no-preference choice. Existing advanced numeric priorities are
preserved when unrelated evidence is edited.

The optional savings-plan `promotional` field is now explicitly validated as boolean and documented
as tariff/provenance metadata only. It never participates in route ranking. A non-promotional route
with a lower actual fee therefore always beats a more expensive promotional route.

## Keep cash reserve authorization

The Comdirect Gateway provider-owned investment-cash policy gains a third mode:

- **All eligible cash**: authorize all eligible cash;
- **Cap authorized cash**: authorize at most the configured EUR cap; and
- **Keep cash reserve** (`retain`): authorize `max(eligible_eur - retain_eur, 0)`.

A retained amount above current eligible cash therefore authorizes zero rather than failing. The
private policy-state format advances to schema 2 while remaining backward-compatible with existing
schema-1 `all_available` and `capped` state.

`retain_eur` is additive REST portfolio schema-1 metadata. Existing all-available/capped payloads
remain wire-compatible with prior versions; use aligned v1.35.2 integration/Gateway packages before
enabling the new retained-cash mode because older strict clients do not know the new optional field.

## Long-running compatibility contracts

- v1.33.0 source-freshness and plan-schedule separation remains preserved; v1.35.2 does not change any configured freshness threshold.
- Recurring scheduling remains anchored to the latest valid Portfolio Architect evaluation.
- v1.35.1 Comdirect session-maintenance resilience remains unchanged.

## Compatibility and security invariants

- Portfolio payload schema 8: unchanged.
- REST portfolio schema 1: unchanged; `retain_eur` is additive and emitted only for retained-cash policy.
- Gateway health schema 6: unchanged; schemas 1–5 remain supported.
- Broker schemas 1/2/3 remain runtime-compatible; the native editor deliberately edits only schema 2/3.
- v1.35.0 provider-scoped cash, exact directed funding topology and advisory-only semantics remain intact.
- v1.35.1 Comdirect connection-error classification and maintenance-worker containment remain intact.
- Verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-plaintext fallback remain unchanged.
- This release does not move PDF parsing into Portfolio Architect; Trade Republic statement import/private diagnostics remain provider-side and unchanged.
- DKB live Gateway acquisition remains a later provider-specific milestone; DKB remains experimental, manual-only and non-live with no authenticated holdings path.
- No trading, order, transfer, payment, or transaction-history capability is introduced; no automatic sell capability is added.
- Native dynamic portfolio presentation remains a separate future milestone.
- The historical `v1.19.0-rc2` brokerage probe remains excluded and is not promoted by this release.

See `docs/UPGRADE-1.35.2.md`.
