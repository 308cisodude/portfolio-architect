# v1.30.0 validation

Portfolio Architect v1.30.0 is a provider-aware execution-policy release based on the
published and live-accepted v1.29.0 baseline.

Release-specific validation must prove:

- integration, engine, common Gateway and all three App versions align at `1.30.0`;
- broker schema 1 preserves established single-provider execution behavior;
- broker schema 2 accepts only bounded provider IDs/names/provenance, explicit evidence
  dates and a bounded freshness window;
- future-dated provider evidence is rejected and stale provider evidence cannot become
  an eligible route or satisfy fee policy;
- fresh savings-plan routes are compared across providers by actual fee, with provider
  priority used only as an economic tie-breaker;
- provider-local manual-order profiles are evaluated without changing the established
  schema-1 Comdirect fee formula;
- purchase recommendations expose only bounded provider ID/name/evidence-date metadata;
- portfolio acquisition source does not implicitly select an execution provider;
- `savings_plan_required` and `free_savings_plan_preferred` evaluate all fresh eligible
  execution providers;
- exceptions schema 2 can bind an accepted finding to a preferred execution provider;
- a changed preferred provider produces `review_required`, reactivates the original
  severity, removes the item from the accepted-exception count and preserves the prior
  decision metadata;
- scheduled exception-review dates include only currently accepted exceptions, while
  historical decision dates also remain visible for review-required exceptions;
- the private decision trace detects execution-provider changes and loads pre-v1.30
  persisted snapshots without provider metadata;
- English/German purchase Tiles use only native Home Assistant state-content attributes
  to show the execution-provider name;
- English/German policy references show a bounded amber exception-review Tile only in
  `review_required` state;
- the v1.29 optimisation-opportunity hierarchy remains intact;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain unchanged;
- v1.27 private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS
  pinning and no-plaintext fallback remain unchanged;
- Comdirect OAuth/session maintenance, Trade Republic statement import and the v1.28
  DKB FinTS registration/capability-probe boundary remain unchanged;
- v1.28.1 immutable action pins and v1.28.2 Dependabot grouping remain unchanged; and
- no trading, order placement, transfer, payment or transaction-history capability is
  added.

The complete local regression/release/privacy/reproducibility pipeline remains required.
Protected GitHub **Validate release** remains authoritative for actual provider-App
Docker/TLS smoke execution because Docker is unavailable in the preparation environment.

Live acceptance should first prove an unchanged healthy schema-1 installation. A second
explicit acceptance step may then opt into schema-2 fee evidence to prove the
provider-change/exception-review path without conflating software upgrade with broker
configuration migration.
