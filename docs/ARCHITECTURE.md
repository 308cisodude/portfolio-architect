# Architecture

## Data path

```text
one primary source + optional DKB CSV supplements
                    ↓
       provider-specific validation
                    ↓
          canonical source positions
                    ↓
       ISIN-based identity resolution
                    ↓
       one consolidated EUR portfolio
                    ↓
 allocation, policy, coverage, and plan engine
                    ↓
       validated payload schema 8
                    ↓
        Home Assistant entities/dashboard
```

Each source is parsed in isolation. Cross-source aggregation occurs only after
its positions and source-owned timestamp validate successfully.

## Identity and provenance

ISIN is the canonical cross-bank identifier. The primary source supplies the
canonical WKN and name. Every consolidated holding can retain a bounded list of
machine-safe source IDs and exact per-source EUR contributions. The engine sees
one holding, so overlapping instruments do not distort target coverage or create
duplicate purchase candidates.

## Freshness

The newest source timestamp becomes the evaluation timestamp, while the oldest
contributing source timestamp controls whether the aggregate remains fresh. This
prevents a live primary source from making an old supplemental export look fresh.

## Failure containment

The Gateway runs in a separate supervised App container. Home Assistant stores a
private, validated last-known-good calculation bound to the source configuration.
The source list is included in that binding, so changing a supplemental path
cannot restore a cache created for a different aggregate.

Same-depot DKB exports are collapsed before aggregation by selecting the newest source-owned export date. This prevents historical CSV files from double-counting one portfolio.

## Allocation overview presentation contract

Version 1.13.0 adds a presentation-only adapter in
`allocation_overview.py`. It consumes the already validated `PortfolioData`
model and publishes a bounded attribute schema through
`sensor.portfolio_architect_allocation_overview`.

The adapter does not recalculate allocation status, modify the ±1 pp corridor,
or influence proposed purchases. It groups and sorts the validated positions,
rounds copies of presentation values deterministically, and keeps the original
per-position entities as the authoritative native Home Assistant interface.

Version 1.13.1 clarifies that this aggregate entity is a data contract, not a
second reference-dashboard summary. The bilingual dashboard continues to use the
established native per-position and plan entities.

## Plan delta and decision trace

Version 1.18.0 adds a Home Assistant-side temporal adapter after complete payload
validation. It snapshots only the bounded provider-neutral fields needed to compare
the two most recent fresh evaluations. The source payload and Gateway contracts do
not change.

```text
validated PortfolioData
          ↓
bounded evaluation snapshot
          ↓
private two-snapshot history
          ↓
deterministic PlanDelta
          ↓
sensor.portfolio_architect_plan_change
```

REST last-known-good replay is outside this advancement path. A degraded refresh
can republish the validated cached portfolio, but it cannot become a new decision
baseline. Trace storage is non-authoritative: persistence failure is logged and
never changes the portfolio result. See `docs/DECISION-TRACE.md`.

## Native dashboard presentation boundary

Version 1.14.0 keeps long policy-exception rationale out of dashboard-triggered
more-info dialogs. The dashboard renders a bounded, compact exception summary and
its separate review/decision metadata. The complete structured exception remains
available through the entity model and diagnostics, while presentation stays
native, responsive, and free of horizontal overflow.

Version 1.15.0 restores the normal tile interaction through a separate bounded
exception-detail entity. That entity copies only the small operational subset
needed by the native dialog and deliberately excludes rationale text and exception
identifiers. The original policy-finding entity remains authoritative for full
diagnostics and explainability work.

## Cost-aware execution and investment reserve

Version 1.16.0 adds an optional execution layer after the existing allocation
and policy calculations. The target architecture, drift corridor, and desired
allocation remain unchanged; the new layer determines whether a purchase is
economically executable through a configured route.

```text
validated portfolio + contribution/reserve
                    ↓
      existing target-gap calculation
                    ↓
      route-specific fee estimation
                    ↓
 configurable execution policy and limits
                    ↓
 bounded purchase or explicit deferral
```

The feature is disabled by default so existing installations retain their
established recommendation behaviour until the operator opts in.

Execution routes have deliberately different cash semantics:

- a free savings plan invests the configured gross cash amount without an order
  fee;
- a percentage-fee savings plan treats the savings-plan rate as gross cash and
  derives the net principal plus fee from it;
- a manual order estimates commission, venue, and settlement charges separately,
  then requires enough reserve for principal plus estimated fees.

The execution policies are:

- `monthly_continuity`: execute each scheduled period and disclose the cost;
- `balanced`: prefer the configured fee ceiling but stop deferring after the
  configured period limit;
- `efficiency_first`: defer until the fee ceiling is met.

The Gateway may publish one optional `investment_reserve` object in REST schema 1.
It contains only a bounded EUR amount and timestamp. The selected Comdirect
account identifier stays in App-private storage. The Gateway computes usable
cash conservatively as the lower of the booked balance and available cash,
clamped at zero, and omits the reserve if either field is unavailable or invalid.

The reserve is advisory input only. Neither the Gateway nor the Home Assistant
integration contains an order, transfer, or payment operation.

## v1.19.0-rc1 experimental fee-probe adapter

The probe is an App-Ingress-only adapter beside, not inside, the scheduled Gateway
snapshot pipeline. The App controller exposes two fixed operations to
`ComdirectClient`: one instrument read and one ex-ante cost calculation. The
transport owns the exact API paths; no caller can supply a path or arbitrary HTTP
method.

The controller maps private depot and venue identifiers to random process-local
browser tokens. A cost request can use only a depot discovered in the current
process and a venue returned by the immediately retained instrument probe. The
public portfolio server and health document do not import or reference probe state.

Probe results are bounded, sanitized value objects kept in memory. The architecture
deliberately does not add a new public Gateway schema, Home Assistant coordinator
source, portfolio payload field, or persistence format.
