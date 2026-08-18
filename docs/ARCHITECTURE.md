# Architecture

## Data path

```text
one primary source + optional REST/CSV supplements
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
The source list, including bounded additional REST provider/endpoint identities, is
included in that binding. Changing a supplemental path or Gateway set therefore
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

Version 1.26.0 extends only the Home Assistant-side aggregation boundary: an existing primary REST Gateway can be joined by additional independently authenticated Gateway REST snapshots. Every additional Gateway must prove health-schema-6 provider identity and snapshot integrity before it participates. The aggregate remains atomic; a configured provider failure reuses the previous complete matching LKG rather than silently dropping that provider. Source-instance count remains separate from distinct-provider count, while existing per-position provenance is preserved.

Version 1.26.1 makes instrument identity explicitly ISIN-first across normalized
target matching and multi-source aggregation. A WKN is fallback identity only when
ISIN is unavailable; when both values exist, WKN is secondary consistency evidence.
Contradictory ISIN/WKN pairs, a WKN mapping to multiple ISINs, or multiple WKNs for
one ISIN fail closed rather than being merged heuristically. REST schema 1 remains
unchanged: a provider may use an ISIN as its generic `identifier` without that value
being mislabelled as a WKN inside the calculation engine.

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

## v1.26.2 presentation and source-failure diagnostics

The Home Assistant integration keeps native entity states machine-readable and
stable. The bilingual reference dashboard may be displayed while Home Assistant's
global frontend language is different, so v1.26.2 adds explicit presentation
attributes for German dashboard state values rather than changing the underlying
entity states.

Configured-source failure identity is also separate from private transport
configuration. The coordinator exposes bounded source-instance IDs and derived
English/German summaries for unavailable sources. Gateway labels contain only the
bounded provider ID; DKB CSV labels contain only a bounded configured instance
number. Endpoint URLs, bearer tokens and file paths are not part of presentation
metadata or diagnostics.

Failure collection does not weaken atomic aggregation. Several additional Gateway
failures may be collected so the operator can see all affected configured sources,
but any such failure still prevents a partial live aggregate and retains only a
matching complete Home Assistant LKG or fails closed.

## v1.26.3 dashboard presentation proxy boundary

Actionable recommendation entities keep their fail-closed Home Assistant
availability semantics. The reference dashboard must not make those entities
artificially available merely to force locale-specific text. Instead, the
always-available plan-actionability entity may expose bounded dashboard-only
presentation attributes derived from the same coordinator state. German tiles use
those attributes only for display and direct their more-info action to the original
metric entity.

Policy evaluation counters remain native entities even when omitted from the
primary reference dashboard. Dashboard layout is presentation policy, not a change
to the policy engine or its machine-readable findings.
## v1.26.4 native date presentation boundary

Schedule and policy dates remain native Home Assistant `SensorDeviceClass.DATE`
entities backed by Python `date` values. Version 1.26.4 deliberately avoided
duplicating those values into locale-specific attributes and instead asked Tile
cards to apply generic `state_content: state` plus `time_format` date formatting.

Live acceptance showed that Home Assistant does not route a `sensor` with device
class `date` through that Tile formatter, so the visible state remained raw ISO
`YYYY-MM-DD`. The authoritative sensor model itself was correct and was retained
unchanged for v1.26.5. Refresh timestamps were unaffected.

## v1.26.5 authoritative-date / presentation-date split

Live acceptance showed that Home Assistant's Tile `time_format` is not applied to a
`sensor` merely because it uses `SensorDeviceClass.DATE`. Portfolio Architect
therefore keeps the established `sensor.portfolio_architect_*` date entities as the
authoritative machine contract and adds a separate, additive Home Assistant
`date`-platform presentation layer for the five dates shown in the reference
dashboard.

Each `date.*` counterpart returns the same Python `date` value as its authoritative
sensor, without string reformatting, timezone conversion, or conversion through a
fabricated `datetime`. The reference dashboard uses those counterparts only as the
visible Tile entity; state/availability conditions and all calculation semantics
continue to reference the original sensors.

Home Assistant's `date` domain normally represents an input. Portfolio Architect's
presentation entities are deliberately read-only: `date.set_value` is rejected
fail-closed, and the reference dashboard routes Tile more-info actions to the
authoritative sensor counterparts so the editable date control is not presented as
a valid write path.
The integration adds no service that can modify planning or policy dates.

## v1.26.6 non-live Gateway source-diagnostics invariant

Unavailable-source identity is derived from effective REST Gateway health, not from
which cache layer happens to retain the trusted portfolio. A reachable primary
Gateway can be non-live while still serving its own last-known-good snapshot; in
that state Portfolio Architect may not need its separate Home Assistant LKG, but the
provider is still the source preventing a fully live aggregate.

Accordingly, each configured REST Gateway whose observed operating mode is not
`live` contributes its bounded `gateway:<provider_id>` identity to the existing
unavailable-source metadata. Transport/authentication/integrity errors and DKB CSV
source failures retain their existing collection paths. This affects diagnostics
only: configured-source atomicity, accepted snapshot calculation, actionability,
provider acquisition and both REST/health wire schemas are unchanged.


## v1.26.7 cold-restart snapshot identity invariant

REST schema-1 snapshot identity is content-derived: the body, SHA-256 and ETag must remain stable when an unchanged persisted snapshot is reloaded after a Gateway restart. Optional position `quantity` is therefore parsed and restored alongside the other canonical position fields rather than being dropped during cache reload.

HTTP conditional evaluation follows validator precedence: when `If-None-Match` is present it is authoritative. A matching ETag may return `304`; a non-matching ETag proceeds to `200` and `If-Modified-Since` is not consulted. Date validation is used only when no ETag validator is supplied. This prevents a timestamp-stable but content-changed representation from being described as not modified.

## v1.27.2 verified Gateway transport architecture

The provider boundary now has two independent authentication layers: TLS authenticates
the internal Gateway service identity and protects transport confidentiality/integrity,
while the existing bearer token continues to authorize the fixed GET-only Portfolio
Architect API. The bearer token is never used as a substitute for certificate
verification and is never distributed through Supervisor discovery.

Each official Supervisor App owns one persistent private CA under
`/data/gateway/tls`. A server leaf certificate is issued for the Supervisor-assigned
internal App hostname. Normal leaf renewal reuses the same CA; corrupt/incomplete CA
state fails closed instead of generating a new trust root. This separates routine
certificate lifecycle from trust-anchor lifecycle.

The public trust path is Home Assistant Supervisor discovery. Once the HTTPS listener
is running, the App publishes only a bounded provider ID, internal hostname/port/fixed
path, public CA certificate and CA SHA-256 fingerprint. Portfolio Architect validates
that record and creates a hostname-checking TLS client context. Supervisor-discovered
private CA trust is explicit: the private CA is loaded without adding the operating
system public root store.

The established SSRF/DNS-race controls remain layered underneath TLS. The endpoint
hostname is resolved and constrained to local/private addresses; the validated answer
set is pinned into the request-scoped connector; the original hostname remains in the
URL so the HTTP Host header, TLS SNI and certificate-name verification refer to the
same identity. Redirects, ambient proxies and cookies remain disabled.

Existing v1.26.x HTTP entries are a bounded migration state only. The v1.27 Home
Assistant integration is installed first. When a matching upgraded App publishes
discovery, Portfolio Architect proves the new HTTPS health endpoint with the existing
bearer token and expected provider identity before atomically persisting `https://`
and the CA. A secured source is never automatically downgraded, and discovery with a
different CA fingerprint never silently replaces existing trust.

Version 1.27.2 makes the Home Assistant config-flow boundary precise. The integration
does not use manifest-level `single_config_entry`, because that framework shortcut
prevents trusted Supervisor `hassio` discovery from being initialized when the one
intended entry already exists. Manual `async_step_user` setup instead checks for any
existing Portfolio Architect entry and aborts, while the stable unique ID remains a
second duplicate guard. `async_step_hassio` still requires zero entries for initial
Comdirect setup or exactly one entry for migration/supplemental handling; it never
uses discovery as permission to create an arbitrary second Portfolio Architect
instance.

## v1.33 source freshness and plan schedule are separate controls

Portfolio Architect no longer treats a recurring plan review date as a substitute for provider
evidence freshness. Every contributing source has an evidence kind and an effective bounded age
threshold. Aggregate source freshness is true only when every source satisfies its own threshold;
invalid or materially future timestamps fail closed.

Existing installations migrate conservatively. If no v1.33 evidence-kind threshold has been
explicitly stored, all kinds inherit the pre-v1.33 global `freshness_hours` value. Provider
classification therefore cannot silently make a previously stale portfolio actionable.

Recurring execution/review scheduling remains planning context. It supplies planned execution and
review dates but does not authorize old bank evidence. Conversely, review due/overdue state does
not mutate the source-freshness result.

The target-plan definition and schedule persistence boundaries are also distinct. Restoring the
file-based target plan removes only Home Assistant target/budget override fields; schedule timing,
source configuration, execution policy and runtime safeguards remain separate options.
