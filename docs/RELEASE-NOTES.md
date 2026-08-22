# Portfolio Architect 1.43.0

Portfolio Architect v1.43.0 is an **execution-evidence governance release**. It allows each schema-2/schema-3 savings-plan provider/ISIN route to carry its own `source` + `as_of` evidence pair, so unrelated routes at one provider no longer need to share one freshness date. It also adds native editing for existing exact directed funding-transfer edges.

## Route-level evidence and freshness

Savings-plan routes may now contain bounded route-specific provenance:

```yaml
savings_plans:
  IE0000000001:
    available: true
    fee_pct: 0.0
    promotional: false
    status: user_verified
    source: route-specific ex-ante cost information
    as_of: 2026-08-22
```

When the pair is present, v1.43 evaluates it independently with the existing `fee_data_max_age_days` window. A stale route fails closed even when provider-level evidence is fresh. Conversely, fresh explicit route evidence remains eligible when the provider-level fallback record is stale; provider-local manual-order profiles continue to depend on provider-level evidence.

Existing savings-plan routes without route-level provenance remain fully backward compatible and inherit provider-level evidence/freshness exactly as before v1.43. There is no automatic broker-file rewrite during upgrade. New native route entries always record explicit route evidence, while editing a legacy route pre-fills its provider fallback and writes explicit route provenance when saved.

## Native editor improvements

The established **Edit savings-plan route** flow now edits route evidence together with availability, fee, promotional status, and evidence status.

The **Funding topology** menu gains **Edit funding transfer**. The exact directed source/destination identity remains immutable while editing; only fee, conservative settlement business days, evidence source, and evidence date may change. This avoids the previous remove/re-add workflow for ordinary evidence refreshes while preserving exact one-way topology and duplicate-edge rules.

## Compatibility and unchanged behavior

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported.
- presentation schema 2 remains unchanged.
- broker schemas 1/2/3 remain unchanged.
- route ranking economics, v1.41.1 local-cash tie-break, provider-scoped cash, and funding-transfer cost ordering are unchanged.
- The v1.33.0 source-freshness and plan-schedule separation remains unchanged: recurring scheduling stays anchored to the latest valid Portfolio Architect evaluation, and v1.43.0 does not change any configured freshness threshold.
- v1.42 normalized execution-path sensor and bilingual native dashboard renderer are unchanged; no dashboard migration is required.
- The v1.39.0 colourful paired allocation Tile view was not included in v1.38.1; the current native allocation and drift presentation remains unchanged.
- Trade Republic `DEPOTAUSZUG`/`KONTOAUSZUG` acquisition is unchanged; Trade Republic PDF parsing remains provider-isolated and does not move PDF parsing into Portfolio Architect.
- Comdirect OAuth/session/cash behavior is unchanged. DKB live Gateway acquisition remains a later gated milestone; the anonymous capability probe remains fail-closed.
- Verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning, provider isolation, and fail-closed provider behavior remain unchanged.
- The historical v1.19.0-rc2 state remains historical and is not promoted by this release.
- No trading, order, transfer, payment, or transaction-history capability is introduced; sell and withdrawal capability likewise remain absent.

## Upgrade

Update the integration and all three Gateway Apps in place to v1.43.0. Existing broker configuration remains valid without changes. No dashboard YAML replacement is required. Operators may migrate individual legacy savings-plan routes to explicit route-level provenance over time by editing and saving them through the native Configure flow or by advanced YAML editing.
