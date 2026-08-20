# Portfolio Architect 1.40.0

Portfolio Architect 1.40.0 strengthens the existing provider-scoped advisory funding topology by allowing each exact directed broker-schema-3 transfer edge to carry explicit operator-owned evidence provenance. A transfer relationship can now record the verified fee and conservative same-/multi-business-day availability assumption together with a bounded evidence source and evidence date. Portfolio Architect still moves no money and places no orders.

## Evidence-backed funding edges

Broker schema 3 continues to use explicit directed transfer relationships. v1.40 adds optional `source` and `as_of` fields to an edge:

```yaml
funding_transfers:
  - from_provider: broker_a
    to_provider: broker_b
    fee_eur: 0
    settlement_business_days: 0
    source: user-verified instant transfer
    as_of: '2026-08-18'
```

The example is synthetic. Portfolio Architect does not infer a fee, timing assumption, reverse edge, bank capability or transfer rail from provider names.

When evidence provenance is present, both fields are required. Future-dated evidence is rejected. The edge uses the existing broker `fee_data_max_age_days` window: once stale, the relationship remains valid configuration evidence but becomes ineligible for route selection until refreshed. This means old observations cannot silently remain actionable forever.

Legacy schema-3 edges without `source`/`as_of` remain accepted for backward compatibility. The native editor creates only evidence-backed edges from v1.40 onward.

## Planning semantics

Existing route economics are preserved. Portfolio Architect evaluates execution provider and funding provider together, includes the configured transfer fee in route cost, uses conservative settlement business days only as a deterministic tie-break after economic cost, and charges one fixed transfer fee per directed edge within an allocation run. Provider-owned cash pools remain separate.

A stale evidenced edge behaves as if that cross-provider route is unavailable. Same-provider cash remains locally usable without a transfer edge.

## Native editor

The Funding topology editor now asks for:

- source provider;
- destination provider;
- verified fee;
- conservative settlement business days;
- evidence source; and
- evidence date.

The evidence fields are local configuration metadata. They are not credentials and are not sent to a provider.

## Preserved contracts

Historical experimental `v1.19.0-rc2` brokerage-diagnostic work remains excluded and is not promoted by this release.

- payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged; schemas 1–5 remain supported;
- presentation schema 2: unchanged;
- broker schemas 1/2/3: retained, with only the optional schema-3 edge provenance described above;
- verified private-PKI HTTPS, bearer authentication and provider isolation: unchanged.
- v1.35.1 Comdirect OAuth/session-maintenance resilience: unchanged;
- Trade Republic local/private statement import: unchanged; this release does not move PDF parsing into Portfolio Architect and no cash or transaction-history parser is added;
- DKB remains experimental, manual-only and non-live; DKB live Gateway acquisition remains a later authenticated milestone;
- private-PKI verified HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-plaintext fallback: unchanged;
- no trading, order placement, transfer execution, payment, transaction-history or automatic-sell capability is added.

## Security and scope

No provider acquisition code changes. No Trade Republic private API, FinTS holdings path, transfer initiation, payment initiation, transaction execution, order placement, order cancellation or sell capability is introduced. The v1.39 colourful dynamic allocation tiles, v1.38.1 drift presentation, provider cash authorization, private-PKI HTTPS, bearer authentication and fail-closed provider isolation remain intact.

Payload schema 8, REST portfolio schema 1, Gateway health schema 6 and presentation schema 2 are unchanged. Broker schemas 1/2/3 remain supported; schema 3 gains only the optional provenance fields described above.

Historical preservation notes: the colourful paired current/target Tile view was not included in v1.38.1; it arrived in v1.39.0 and remains unchanged here. The v1.33.0 source-freshness and plan-schedule separation remains unchanged: recurring scheduling stays anchored to the latest valid Portfolio Architect evaluation, source timestamps remain evidence-only freshness inputs, and v1.40.0 does not change any configured freshness threshold.

No trading, order, transfer, payment, or transaction-history capability is introduced by v1.40.0.

No dashboard YAML migration is required for v1.40.0.
