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

## Provider Gateway boundary

Version 1.24.0 separates the common Gateway runtime from the provider client type.
The authenticated HTTP server, snapshot storage, health/LKG state and provider-neutral
REST model consume a minimal `PortfolioProvider` contract: a bounded provider ID, a
validated refresh cadence and `fetch_snapshot()`. The common server does not import
`ComdirectClient`.

The released provider remains Comdirect. Its OAuth/bootstrap, account discovery,
selected-account persistence and cash-authorization semantics stay provider-specific.
Gateway health schema 6 adds only the non-secret `provider_id`; health schemas 1–5
remain available unchanged. This creates the stable seam for separate DKB and Trade
Republic Apps without pretending those provider runtimes already exist. See
`docs/GATEWAY-PROVIDERS.md`.

Version 1.24.1 fixes the reduced DKB/TR shell packaging without expanding that boundary: the optional Comdirect `GatewayConfig` type import is evaluated only during static type checking, while runtime server code remains based on `ServerConfig`.

Version 1.25.0 adds provider-specific document acquisition only inside the Trade Republic App. The PDF parser and import Ingress handler are not copied into Comdirect, DKB, or the standalone Gateway. A validated statement is converted to the existing `PortfolioSnapshot` model before the common authenticated REST server sees it; the uploaded PDF itself is processed in memory and discarded.

## Graceful degradation and actionability

Version 1.20.0 separates **trusted informational continuity** from **authorization
to create a new investment action**. A validated REST calculation may be retained
as Home Assistant last-known-good while it remains inside the bounded cache
retention window. An incoming snapshot that regresses in time or fails fingerprint,
position-count, or health cross-checks is rejected and cannot replace that accepted
calculation.

Version 1.20.1 makes coordinator notifications part of that boundary: a completed update cycle publishes changed health/LKG/actionability metadata even when the retained portfolio calculation is byte-for-byte equivalent to the previous one. This prevents stale live entity states from masking degraded operation.

```text
trusted live snapshot
        │
        ├── healthy + fresh + live ──→ informational data + actionable plan
        │
        └── source degrades ─────────→ trusted LKG informational data
                                      holdings / allocation / policy remain
                                      cash authorization / new purchases stop
```

For REST sources, actionability requires fresh data, available Gateway health, no
active integrity failure, no Home Assistant LKG replay, no reauthentication
requirement, and effective `live` operating mode. This is an output-boundary
control as well as a presentation choice: stale authorized cash and purchase
recommendations are made unavailable rather than being presented as current.

The Home Assistant LKG retention limit uses a positive Gateway-advertised maximum
cache age when known and otherwise falls back to seven days. Normal data freshness
remains a separate, shorter policy; exceeding the freshness window can leave
holdings visible while making the plan non-actionable.

Refresh-overdue telemetry follows the same evidence rule. The coordinator records
when a health document was observed. A scheduled deadline can be classified as
overdue only if a health observation obtained at or after the deadline plus grace
still advertises that missed deadline. Local passage of time cannot turn an old
health sample into proof of failure. Snapshot age and expiry are derived locally
from the accepted timestamp.

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

Version 1.18.1 adds a Home Assistant-side temporal adapter after complete payload
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
From v1.19.0 its amount is explicitly the cash the Gateway authorizes Portfolio
Architect to allocate. The selected Comdirect account identifier stays in
App-private storage. The Gateway first computes eligible cash conservatively as
the lower of booked balance and available cash, clamped at zero, then applies its
provider-owned `all_available` or `capped` authorization policy.

An additive `investment_cash` object can explain the decision with the bounded
booked account balance, eligible cash, authorized cash, policy, optional cap, and
timestamp. The legacy reserve amount must equal the authorized amount. This keeps
allocation provider-neutral while allowing each future Gateway to enforce its own
cash policy.

The reserve is advisory input only. Neither the Gateway nor the Home Assistant
integration contains an order, transfer, or payment operation.

## v1.21 execution semantics

Portfolio Architect keeps recurring schedule context separate from present recommendation validity. `planned_execution` remains the stable entity identifier for the execution date associated with the latest evaluation, but the user-facing concept is **Scheduled execution**. The date may be in the past without proving that an order occurred or forcing the recommendation to expire.

Current actionability is derived independently from source freshness/trust, REST/LKG/integrity health, the current execution state, and the relationship between today's date and the scheduled date. The native `plan_actionability` entity exposes only bounded states and metadata; it cannot execute orders and it does not infer transaction history.
