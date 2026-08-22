# Upgrade to Portfolio Architect 1.43.0

Version 1.43.0 moves savings-plan fee evidence to the provider/ISIN route where it belongs and adds native editing for existing directed funding-transfer edges. It does not change provider acquisition, recommendation economics, Gateway wire schemas, dashboard presentation, or Portfolio Architect's advisory-only boundary.

## Route-level savings-plan evidence

Schema-2 and schema-3 savings-plan entries may now carry an optional bounded evidence pair:

```yaml
providers:
  example_broker:
    name: Example Broker
    source: provider-level fallback evidence
    as_of: 2026-08-01
    savings_plans:
      IE0000000001:
        available: true
        fee_pct: 0.0
        promotional: false
        status: user_verified
        source: route-specific ex-ante cost information
        as_of: 2026-08-22
```

When route-level `source` + `as_of` is present, both fields are required. The route uses the existing `fee_data_max_age_days` window independently from the provider-level record:

- stale route evidence fails closed even when provider-level evidence is fresh;
- fresh route evidence may remain eligible even when provider-level fallback/manual-order evidence is stale;
- future-dated or partial route evidence is rejected.

Existing routes without route-level provenance remain valid and preserve pre-v1.43 behavior by inheriting the provider-level `source`, `as_of`, and freshness. Portfolio Architect does not rewrite `broker.yaml` automatically during upgrade.

The native **Add savings-plan route** form now records explicit route evidence. The existing **Edit savings-plan route** form pre-fills provider evidence when opening a legacy route; saving the form makes that route's evidence explicit. Provider-level evidence remains required as the compatibility fallback and as evidence for provider-local manual-order fee profiles.

## Native funding-transfer editing

**Execution providers & funding → Funding topology** now includes **Edit funding transfer** when at least one exact directed edge exists. Editing changes only:

- transfer fee;
- conservative settlement business days;
- evidence source; and
- evidence date.

The configured `from_provider` → `to_provider` identity is locked during edit. Reverse transferability is never inferred. To change direction, remove the old edge and add the exact new direction deliberately.

## Upgrade procedure

1. Update the Portfolio Architect integration to **1.43.0**.
2. Align the Comdirect, DKB, and Trade Republic Gateway Apps to **1.43.0** in place.
3. Reload/restart Home Assistant as required by the normal HACS/App update workflow.
4. Confirm Portfolio Architect remains healthy/live and the current plan is unchanged.
5. No dashboard YAML replacement is required; the v1.42.0 execution-path dashboard remains current.
6. Existing broker configuration requires no immediate migration. Refresh route evidence deliberately when appropriate through the native editor or advanced YAML editing.

## Preserved boundaries

- broker schemas 1/2/3 remain unchanged;
- payload schema 8, REST portfolio schema 1, Gateway health schema 6, and presentation schema 2 remain unchanged;
- v1.41 Trade Republic holdings/cash acquisition and v1.41.1 local-cash tie-break are unchanged;
- v1.42 execution-path presentation is unchanged;
- Comdirect/DKB/Trade Republic provider acquisition is unchanged apart from normal version alignment;
- verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning, and provider isolation are unchanged;
- no transfer initiation, payment API, trading, order placement/cancellation, sell, withdrawal, or transaction-history capability is added.
