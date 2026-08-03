# v1 stability contract

Portfolio Architect v1 treats the following as stable public interfaces:

- payload schema 8;
- existing clean Home Assistant entity IDs and unique IDs;
- language-neutral machine states and identifiers;
- complete-portfolio and current-plan scope semantics;
- buy-only recommendation behaviour;
- canonical provider-neutral position semantics;
- read-only source access with no broker write operation.

Compatible additions may introduce new optional payload fields, entities,
translations, diagnostics, plan configuration, or source adapters. A release
that removes or redefines a stable field, entity, scope, or recommendation rule
requires a new major version and an explicit migration path.

## Source adapters

v1.3 established Comdirect and generic CSV adapters. v1.4 added the optional
`local_rest_json` adapter, v1.5.0 supplied its standalone Comdirect gateway, and
v1.5.1 adds a native Home Assistant App deployment. All source adapters
normalize to the same canonical
`Position` model before the engine runs. Selecting another adapter may change
the source timestamp and source-provider diagnostic state, but it must not change
payload schema, plan scope, policy semantics, or recommendation rules.

Existing CSV entries migrate from config-entry schema 6 to 7 without changing
their stored source data. The REST endpoint and token are added only through an
explicit setup or Reconfigure flow.

The REST JSON source schema is independently versioned as schema 1. Unsupported
versions fail closed rather than being guessed. A future incompatible REST
contract requires a new adapter/schema path; it must not silently reinterpret
schema 1.

## Entity and statistics compatibility

The historical entity ID
`sensor.portfolio_architect_monthly_contribution` remains stable. Its visible
name is **Contribution per execution**, which accurately describes schedules
with multiple executions per period.

Contribution, allocated-contribution, unallocated-contribution, and
per-instrument proposed-buy entities retain `state_class: measurement`, preserving
the v1.3.1 long-term-statistics contract.

## Configuration and presentation

Relative local paths and source-adapter settings are config-entry data and may
be changed only through the native Reconfigure flow. UI plan overrides remain
config-entry options; local YAML remains a read-only fallback.

The supplied dashboard is versioned presentation rather than a dynamic API. New
holdings and plan instruments receive entities automatically, while static
Distribution-card and per-instrument entity lists still require an explicit
dashboard update. v1.5.1 and v1.6.0 do not require a dashboard change. v1.6.1 requires the supplied dashboard update for the ISIN tap/hold interaction and Gateway health cards.

## v1.6.0

v1.6.0 is a presentation and metadata release. It does not modify the calculation
engine, source adapters, config-entry schema, payload schema, entity IDs or
dashboard layout. The native Gateway App runtime remains the validated v1.5.6
protocol implementation with matching branding assets.


## v1.6.1

v1.6.1 adds compatible diagnostic and identifier entities without changing any
existing unique ID or calculation state. The Gateway App is promoted to stable
after live validation. The authenticated Gateway health contract is additive to
REST schema 1 and does not alter the portfolio snapshot schema.

## v1.7.0

v1.7.0 adds compatible transport-integrity metadata around REST portfolio
schema 1; it does not alter the schema-1 JSON body. The Gateway health endpoint
uses explicit media-type negotiation so older clients retain the original
strict health document. Snapshot fingerprints, counts, diagnostic entities, and
rollback rejection are additive fail-closed controls.

## v1.8.0

v1.8.0 adds explicit last-known-good operation without changing the portfolio
model. A transient bank/API failure can leave the accepted snapshot available
and fresh, while the Gateway and Home Assistant clearly report degraded mode,
refresh-failure count, snapshot age, and remaining cache window. Health schemas
1 and 2 remain available for compatible rolling upgrades.


## v1.9.0

v1.9.0 adds compatible refresh-operation telemetry and a protected App-Ingress
manual action. Health schemas 1 through 3 remain available. The manual action is
not part of REST portfolio schema 1 and does not weaken the bearer API's GET-only
contract. Fixed-cadence scheduling, non-overlap, duration, trigger, and next-run
metadata are additive operational controls.

## v1.10.0

v1.10.0 adds compatible classified recovery metadata through negotiated health
schema 5. Health schemas 1 through 4 remain available. New diagnostic entities
and Repair issues are additive and do not redefine existing entity states,
portfolio calculations, REST portfolio schema 1, or the CSV rollback path.
Failure classifications and recommended actions are stable machine values; raw
upstream error content is not part of the public contract.

## v1.10.1

v1.10.1 adds an integration-local, private last-known-good calculation cache so
a complete Gateway-process outage no longer cascades into unavailable
portfolio, plan, architecture, and policy entities. Cache acceptance is bound
to the REST endpoint and every current calculation input. OAuth refresh errors
are classified from a bounded error code rather than treating all failures as
reauthentication, and the Ingress UI now synchronizes all runtime fields while
open.

## v1.10.2

v1.10.2 corrects persistence of the Home Assistant-side last-known-good cache.
The calculation engine's `Decimal` values are converted to exact decimal strings
before JSON storage and fully revalidated after restoration. This makes the
cache survive integration reloads and Home Assistant restarts as originally
intended by v1.10.1.

## v1.18.0 temporal explainability

Version 1.18.0 adds one additive enum entity and a private two-evaluation trace.
It does not alter source payload schema 8, REST schema 1, Gateway health schema 5,
the allocation corridor, policy decisions, or cost-aware execution. The supplied
dashboard adds only a conditional native tile; older dashboards remain valid.

The trace is advisory and non-authoritative. A failure to restore or persist it
does not make portfolio data unavailable and does not change a recommendation.
