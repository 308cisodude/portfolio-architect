# Execution-provider configuration

Portfolio Architect separates **portfolio acquisition** from **purchase execution**.
A configured source such as a Comdirect Gateway or Trade Republic statement tells PA
where current holdings came from. It does not authorize or imply that future purchases
must execute through that provider.

Provider-aware execution configuration remains persisted in `broker.yaml`. Portfolio Architect 1.35.2 adds a native **Execution providers & funding** options editor for schema 2 and schema 3 files. The editor validates the complete document and replaces `broker.yaml` atomically; direct YAML editing remains an advanced/file-based path. Schema 1 stays readable for compatibility but must be deliberately migrated to schema 2 before the native editor is enabled.

Portfolio Architect 1.35.3 restores the English/German labels for all list-based menus in that editor; the broker document model and write semantics are unchanged.

## Schema 1 compatibility

Existing schema-1 files remain valid and preserve their pre-v1.30 behavior:

```yaml
schema_version: 1
as_of: 2026-07-27
broker:
  id: broker_a
  name: Broker A
  savings_plans:
    IE0000000001:
      available: true
      fee_pct: 1.5
```

Schema 1 represents one execution provider. Its historical `as_of` value remains
informational; v1.30 does not retroactively impose a freshness failure on existing
single-broker installations.

## Schema 2 provider-aware routing

Schema 2 opts into explicit provider-aware execution policy:

```yaml
schema_version: 2
fee_data_max_age_days: 30
providers:
  broker_a:
    name: Broker A
    source: user-verified tariff dated 2026-08-15
    as_of: 2026-08-15
    priority: 20
    savings_plans:
      IE0000000001:
        available: true
        fee_pct: 1.5
    manual_order:
      available: true
      commission_base_eur: 4.90
      commission_pct: 0.25
      commission_min_eur: 9.90
      commission_max_eur: 59.90
      venue_fee_pct: 0.0025
      venue_fee_min_eur: 2.50
      settlement_fee_eur: 2.90

  broker_b:
    name: Broker B
    source: user-verified tariff dated 2026-08-16
    as_of: 2026-08-16
    priority: 10
    savings_plans:
      IE0000000001:
        available: true
        fee_pct: 0
    manual_order:
      available: true
      commission_base_eur: 1.00
      commission_pct: 0
      commission_min_eur: 1.00
      commission_max_eur: 1.00
      venue_fee_pct: 0
      venue_fee_min_eur: 0
      settlement_fee_eur: 0
```

The example values above are **synthetic configuration examples**, not claims about a
particular bank or broker tariff.

### Required evidence

Every schema-2 or schema-3 provider requires:

- a stable lowercase provider ID;
- a human-readable name;
- a bounded provenance/source description;
- an `as_of` date; and
- the common `fee_data_max_age_days` validity window.

A schema-2/schema-3 provider whose evidence is older than the configured validity window remains known
but is **ineligible** for route selection and fee-policy compliance. A future-dated
`as_of` value is rejected.

PA does not scrape brokerage websites, infer current fees from historical purchases,
or silently convert missing data to a zero fee. Updating fee evidence is an explicit
configuration/governance action.

### Route selection

For each instrument PA can evaluate:

- available savings plans and their percentage fees; and
- an optional provider-local manual-order fee formula.

The route with the lowest cost ratio is preferred. For funded schema-3 candidates,
settlement time is considered only after economic cost. `priority` is an optional
deterministic **tie-break preference** after both of those criteria; a lower number wins
the tie. Provider priority cannot make a more expensive route defeat a cheaper route.
Omitting `priority` is the neutral/default choice. The native editor presents preference
semantics rather than requiring numeric priorities, while preserving an existing advanced
numeric value when the user edits unrelated evidence.

The optional per-route `promotional` flag is descriptive tariff/provenance metadata only.
It must be boolean when present and never participates in route ranking. A normal
non-promotional 0% route therefore beats a promotional route with a positive fee.

The selected provider is exposed with the recommendation as bounded metadata:

- `execution_provider`;
- `execution_provider_name`; and
- `execution_fee_data_as_of`.

The provider is planning/explainability data. Portfolio Architect remains advisory and
does not place orders.

## Schema 3 provider-scoped funding topology

Schema 3 keeps the schema-2 execution-provider model and adds explicit **directed**
funding relationships. Cash remains owned by the Gateway/provider that reported it;
Portfolio Architect never treats cash from several institutions as one fungible pool.

```yaml
schema_version: 3
fee_data_max_age_days: 30
providers:
  broker_a:
    name: Broker A
    source: user-verified tariff dated 2026-08-18
    as_of: 2026-08-18
    priority: 20
    savings_plans:
      IE0000000001:
        available: true
        fee_pct: 1.5
  broker_b:
    name: Broker B
    source: user-verified tariff dated 2026-08-18
    as_of: 2026-08-18
    priority: 10
    savings_plans:
      IE0000000001:
        available: true
        fee_pct: 0

funding_transfers:
  - from_provider: broker_a
    to_provider: broker_b
    fee_eur: 1.50
    settlement_business_days: 2
    source: user-verified transfer evidence
    as_of: 2026-08-18
```

The values are synthetic examples. Transfer cost and conservative settlement delay are
operator-owned configuration evidence; Portfolio Architect does not infer them from a
bank name or assume that a standard transfer is free. From v1.40 onward, an edge may
also carry bounded `source` + `as_of` provenance. When one is present, both are required.
The native editor creates only evidence-backed edges.

Evidence-backed edges use the existing `fee_data_max_age_days` window. A future evidence
date fails closed; a stale edge remains valid configuration evidence but is excluded from
route selection until the operator refreshes the observation. Legacy schema-3 edges
without provenance remain supported for backward compatibility.

Same-provider funding is implicit and has no transfer fee or delay. Cross-provider
funding is eligible only when the exact directed edge exists. An edge from `broker_a`
to `broker_b` never authorizes the reverse direction. Unknown providers, duplicate
edges, self-edges, negative/oversized fees, and invalid settlement delays fail closed.

For a planned purchase, Portfolio Architect evaluates **execution provider + funding
provider** together. Its cost ratio includes both the execution fee and any funding
transfer fee. Settlement business days are a deterministic tie-breaker after economic
cost, so locally available cash wins an otherwise equal route. A fixed transfer fee is
counted once per source/destination edge within one allocation run.

When a cross-provider route wins, the advisory payload records:

- the execution provider and execution fee;
- the funding provider;
- whether a transfer is required;
- the configured transfer fee and conservative settlement delay; and
- an aggregate transfer plan containing source, destination, amount required at the
  destination, fee and settlement business days.

Provider-scoped cash output also records both the authorized amount initially available
and the amount remaining after the current recommendations. Gateway cash authorization
remains authoritative per source. Version 1.35.2 supports three modes: `all_available`,
`capped`, and `retain` (UI: **Keep cash reserve**). Retained-cash authorization is
`max(eligible_eur - retain_eur, 0)`, so a retained amount above current eligible cash
cleanly authorizes zero rather than failing.

This is still planning only. Portfolio Architect never initiates the transfer, moves
money, places the resulting order, records transaction history, or assumes that a
recommended transfer/trade actually occurred.

## Route-scoped accepted exceptions

Exceptions schema 2 may record the provider assumption under which an exception was
accepted:

```yaml
schema_version: 2
exceptions:
  - id: example_exception
    instrument_id: IE0000000001
    rule: accumulating_preferred
    status: accepted
    assumptions:
      preferred_execution_provider: broker_a
    approved_on: 2026-07-27
    review_on: 2027-07-27
```

If `broker_a` remains the preferred route, the exception remains
`accepted_exception`. If fresh execution evidence makes another provider preferable,
the original decision is retained for auditability but its current state becomes
`review_required`.

A `review_required` exception:

- no longer contributes to the active accepted-exception count;
- resumes its original policy severity until reviewed;
- reports the expected and newly observed execution provider;
- preserves the original decision date and bounded exception detail; and
- does not continue presenting a future scheduled review date as though the underlying
  assumption were still valid.

Existing schema-1 exceptions without provider assumptions retain their established
behavior.

## Superseded exception history

Schema 2 also permits a historical exception to enter the terminal audit state
`superseded` when the active plan no longer relies on the instrument/decision that
required the exception:

```yaml
schema_version: 2
exceptions:
  - id: old_distribution_exception
    instrument_id: IE0000000001
    rule: accumulating_preferred
    status: superseded
    assumptions:
      preferred_execution_provider: broker_a
    approved_on: 2026-07-27
    last_reviewed_on: 2026-08-17
    review_on: null
    superseded_on: 2026-08-17
    superseded_by_instrument_id: IE0000000002
    superseded_reason: preferred_accumulating_route_available
```

A superseded exception is retained only as validated governance history. It is not an
active exception, does not contribute to accepted/review-required counts, and does not
create a transaction or sell instruction. Its replacement instrument must be distinct
and its audit dates/reason are bounded and fail closed.

The v1.31 current-plan migration uses this lifecycle for the former distributing
Robotics share class: the accumulating share class is the sole active target, while an
already-owned distributing position remains an ordinary outside-plan holding.

### Exact-instrument evidence only

Execution configuration is not a brokerage capability catalogue. Adding one confirmed
provider/instrument savings-plan route does **not** imply that every target instrument is
tradable through that provider. Prefer exact per-instrument entries. Add a provider-wide
manual-order formula only when its availability semantics are actually intended and
evidenced for the instruments PA may evaluate.

## Security and architectural boundary

Provider-aware routing changes only local planning/policy evaluation. It does not:

- add broker credentials;
- broaden Gateway authentication or network permissions;
- change portfolio REST schema 1 or Gateway health schema 6;
- perform trading, order placement, transfer or payment operations; or
- couple portfolio-source identity to execution-provider selection.
