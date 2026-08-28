# Portfolio Architect 1.56.0

Portfolio Architect v1.56.0 is a deliberately narrow UX and hygiene release prepared from the fully published and live-accepted v1.55.1 baseline. It does not change provider identity, acquisition authority, REST portfolio schema 1, Gateway health schema 8 (payload schema 8), `fallback_policy: none`, freshness policy, private-PKI trust, planner economics, or the advisory-only boundary.

## What changes

### Deterministic DKB probe time presentation

The DKB anonymous BPD research page no longer asks the browser to localize the persisted probe timestamp. The App renders the timestamp server-side in two explicit forms:

- deterministic `Europe/Berlin` local time, including the correct CET/CEST offset; and
- the authoritative UTC dispatch timestamp retained by the probe state.

The DKB App installs Alpine `tzdata` so `zoneinfo.ZoneInfo("Europe/Berlin")` is available in the minimal runtime image. The anonymous BPD probe remains research-only. Authenticated DKB FinTS acquisition remains disabled and cannot replace or fall back from CSV evidence.

### Generic Import privacy and discovery lifecycle

The Generic Import bearer token is moved away from the screenshot-prone top of Ingress into a dedicated, collapsed **Sensitive connection material** section near the bottom of the page.

Generic Import now records the exact Supervisor discovery UUID it publishes. On graceful App shutdown it removes that exact discovery record. If cleanup cannot reach Supervisor, the UUID remains in App-private state and is reconciled before any later publication, preventing duplicate self-registration. SIGTERM is routed through the normal graceful server shutdown path so ordinary stop/update/uninstall operations can execute the cleanup.

No provider credentials, CSV bytes, filenames, account identifiers, transaction rows, bearer secrets, or private TLS key material are added to discovery.

### Runtime-health dashboard consolidation

The bilingual reference dashboard reduces overlapping incident presentation:

- one primary **Gateway incident / Gateway-Störung** tile presents the consolidated reason and recommended action;
- one explicit **Snapshot / LKG state** tile appears when Home Assistant is using a last-known-good snapshot;
- ordinary freshness and gateway-status tiles yield to the higher-priority incident/LKG presentation when appropriate;
- redundant standalone reauthentication, attention-reason, recommended-action, failure, and overdue alert tiles are removed while the underlying entities remain available.

This is presentation-only; coordinator state, repairs, diagnostics, automations, LKG behavior, and fail-closed actionability are unchanged.

### Comdirect naming after the completed identity migration

The provider-qualified App `portfolio_architect_gateway_comdirect` is now displayed simply as **Portfolio Architect Gateway — Comdirect**. The historical migration-source package `portfolio_architect_gateway` is displayed as **Comdirect LEGACY** and marked with Home Assistant's native `stage: deprecated` lifecycle flag.

v1.56.x is the final published line for the historical App identity. Its Ingress page explicitly instructs remaining installations to complete the established one-time migration before upgrading beyond v1.56.x. The active App repository is scheduled to withdraw `portfolio_architect_gateway` in v1.57.0, while the canonical Comdirect App will retain the migration receiver compatibility needed by already-installed v1.55/v1.56 legacy instances.

No slug, endpoint derivation, same-CA migration rule, bearer-token preservation, OAuth-session exclusion, migration code, or Portfolio Architect cut-over validation changes in v1.56.0.

### Quieter routine Ingress logging

Routine successful Ingress request-completion messages move from INFO to DEBUG across the Gateway UIs. Explicit startup, acquisition, import, migration, probe, error, and security-relevant messages keep their existing operational log levels.

## Compatibility and non-goals

v1.56.0 intentionally does **not** introduce capability-level acquisition arbitration and does **not** advance authenticated DKB FinTS. Comdirect remains `live_api`/complete-`csv` with explicit operator switching; DKB remains CSV-authoritative; Trade Republic remains PDF-authoritative; Generic Import remains provider-neutral mapped CSV.

The historical Comdirect App remains in the release assets only as a bounded migration source for installations that still need the v1.55 identity migration. A completed installation should run only the canonical provider-qualified Comdirect App.

## Retained compatibility contracts

v1.56.0 deliberately preserves the established wire, planner, and safety contracts:

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 8 current; schemas 1–7 remain supported
- schemas 1–6 remain supported as part of that health-schema compatibility range
- presentation schema 2 remains current
- broker schemas 1/2/3 remain supported
- authenticated DKB FinTS acquisition remains disabled
- Trade Republic remains Gateway-owned PDF acquisition; this release does not move PDF parsing into Portfolio Architect
- the historical v1.19.0-rc2 brokerage capability probe is not promoted by this release and no brokerage probe code is included
- No trading, order, transfer, payment, or transaction-history capability is added
- the v1.33.0 source-freshness and plan-schedule separation remains intact: execution timing is anchored to the latest valid Portfolio Architect evaluation and this release does not change any configured freshness threshold
- the v1.53 acquisition-control compatibility contract required no dashboard YAML replacement; v1.56 changes no runtime contract, while users of the shipped reference dashboard should replace its YAML only to adopt the consolidated presentation

Capability-level acquisition arbitration is not included.
