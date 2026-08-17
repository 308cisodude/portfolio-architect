# Portfolio Architect 1.30.0

Version 1.30.0 is a provider-aware execution-policy milestone prepared from the exact
published and live-accepted v1.29.0 baseline. It separates the provider that supplies
portfolio holdings from the provider through which a future purchase is best executed.
Portfolio Architect remains advisory and read-only.

## Provider-aware execution routes

`broker.yaml` schema 1 remains fully supported and preserves the established
single-provider behavior. A new opt-in schema 2 can describe multiple execution
providers, each with bounded:

- provider identity and display name;
- fee-data provenance text;
- `as_of` date and a common maximum evidence age;
- per-instrument savings-plan availability/fee; and
- optional provider-local manual-order fee formula.

Schema-2 fee evidence that is stale remains known but is ineligible for route selection
or fee-policy compliance. Future-dated evidence is rejected. Portfolio Architect does
not scrape broker sites or infer a missing fee.

For each instrument the planner evaluates fresh eligible savings-plan/manual routes and
prefers the lowest cost ratio. Provider priority is only a deterministic tie-breaker
between economically equal routes.

Recommendations add three optional backward-compatible fields:

- `execution_provider`;
- `execution_provider_name`; and
- `execution_fee_data_as_of`.

The existing payload remains schema 8 because the additions are optional and older
recommendations without provider metadata remain valid.

## Provider-aware fee policy

`savings_plan_required` and `free_savings_plan_preferred` now evaluate across all fresh
eligible execution providers instead of assuming a single broker. A fresh zero-fee
route therefore satisfies the fee preference even when another provider would charge a
fee for the same instrument.

The reference purchase Tiles use native Home Assistant `state_content` to display the
selected execution-provider name beneath the proposed amount. No custom card or
frontend extension is introduced.

## Route-scoped accepted exceptions

Exceptions schema 2 adds one optional bounded assumption:

```yaml
assumptions:
  preferred_execution_provider: comdirect
```

The accepted Robotics exception in the public current-plan fixture is migrated to this
model. While Comdirect remains the preferred execution route the exception retains its
established `accepted_exception` state.

If fresh execution evidence makes another provider preferable, the decision is not
deleted. Instead:

- the finding becomes `review_required`;
- it no longer contributes to the accepted-exception count;
- the original rule severity becomes active again until review;
- the expected and observed provider IDs are exposed as bounded exception-detail
  metadata;
- the original decision date remains visible for auditability; and
- the old future scheduled-review date no longer presents as the next active review.

The English/German reference dashboards show a compact amber **Robotics exception
review / Robotik-Ausnahme prüfen** Tile when this state occurs.

Existing schema-1 exceptions without provider assumptions retain their prior behavior.

## Decision trace

The private two-evaluation decision trace now records the optional execution-provider
ID. A provider change is a material recommendation change with bounded reason code
`execution_provider_changed`. Persisted pre-v1.30 snapshots without this optional field
remain loadable.

## Preserved boundaries

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported
- portfolio-source identity and execution-provider identity remain separate
- provider Gateway acquisition and credentials: unchanged
- v1.27 private-PKI verified HTTPS, bearer authentication, Supervisor trust discovery,
  DNS pinning and no-plaintext fallback: unchanged
- Comdirect v1.27.4 OAuth/session maintenance: unchanged
- Trade Republic statement import/private snapshot behavior: unchanged
- v1.28 DKB FinTS registration/capability-probe gate: unchanged
- v1.28.1 immutable GitHub Actions pins and v1.28.2 Dependabot grouping: unchanged
- v1.29 native dashboard hierarchy: retained
- No trading, order, transfer, payment, or transaction-history capability is added
- the historical `v1.19.0-rc2` experimental brokerage probe is not promoted by this release

DKB remains experimental, manual-only and non-live. DKB live Gateway acquisition remains a later authenticated milestone. `registration_required` remains the expected state until Portfolio Architect receives its own FinTS registration number; any later positive `HIWPDS` result remains bank-level research evidence only. Trade Republic statement import remains provider-isolated; this release does not move PDF parsing into Portfolio Architect.

See `docs/EXECUTION-PROVIDERS.md` and `docs/UPGRADE-1.30.0.md`.
