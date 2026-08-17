# v1.31.0 validation

Portfolio Architect v1.31.0 is a canonical-target/policy-governance correction based on
the published and live-accepted v1.30.0 baseline.

Release-specific validation must prove:

- integration, engine, common Gateway and all three App versions align at `1.31.0`;
- the active Robotics target is accumulating `IE00BYZK4552` / `A2ANH0` and the former
  distributing ISIN is absent from the active allocation;
- metadata for `IE00BYWZ0333` remains available so an imported legacy holding remains
  identifiable after the target migration;
- an existing distributing Robotics position becomes `outside_scope`, retains its
  market value, has no active `plan_fund_id`, and never becomes a purchase
  recommendation;
- the active target architecture reports Robotics missing until an accumulating holding
  exists, while the whole portfolio continues to include the distributing holding;
- the current reference broker configuration uses schema 2 and includes only the
  explicitly evidenced Trade Republic savings-plan route for `IE00BYZK4552`;
- the current reference does not infer provider-wide Trade Republic manual-order
  availability or tradability for unrelated instruments;
- the accumulating Robotics route is the preferred fresh savings-plan route and satisfies
  the zero-fee preference under the configured evidence;
- exceptions schema 2 accepts the historical `superseded` state only with bounded,
  internally consistent supersession metadata;
- future-dated supersession evidence, an invalid replacement instrument, an unknown
  exception state, or malformed audit metadata fails closed;
- superseded exceptions are retained as validated history but do not count as active
  accepted exceptions or review-required exceptions;
- the v1.30 `review_required` provider-assumption semantics remain covered by a
  self-contained historical regression independent of the evolving current plan;
- English/German reference dashboards expose an existing distributing Robotics holding
  in the outside-current-plan section while preserving native-card interaction;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain unchanged;
- v1.27 private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS
  pinning and no-plaintext fallback remain unchanged;
- Comdirect OAuth/session maintenance, Trade Republic statement import and the v1.28
  DKB FinTS registration/capability-probe boundary remain unchanged;
- v1.28.1 immutable action pins, v1.28.2 Dependabot grouping, v1.29 dashboard hierarchy
  and v1.30 provider-aware execution routing remain intact; and
- no trading, order placement, automatic sell, transfer, payment or transaction-history
  capability is added.

The complete local regression/release/privacy/reproducibility pipeline remains required.
Protected GitHub **Validate release** remains authoritative for actual provider-App
Docker/TLS smoke execution because Docker is unavailable in the preparation environment.

Live acceptance must deliberately migrate the user-owned current-plan files after the
software/package upgrade. Before the first accumulating Robotics purchase, six-of-seven
active-target coverage is expected and is not a source-health or LKG failure.
