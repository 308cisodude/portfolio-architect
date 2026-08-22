# Support policy

Portfolio Architect is a community-maintained Home Assistant custom integration.
It is not maintained, reviewed, or supported by Home Assistant, Comdirect, DKB,
or any execution venue.

## Supported versions

Security and correctness fixes are provided for:

- the current stable Portfolio Architect release; and
- the immediately preceding stable release while a documented upgrade path exists.

The Home Assistant support floor for the 1.36.x release line is **2026.7.0**.
The project targets the current and immediately previous monthly Home Assistant
release, subject to automated compatibility checks. Beta releases receive
best-effort compatibility only.

Gateway App versions 1.16.1 and later remain compatible with Portfolio Architect
1.44.0 through the legacy reserve contract. Gateway App 1.19.0 or newer is required
for configurable authorized-cash policy metadata; 1.19.1 or newer contains the
corrected capped-to-all-available Ingress transition. Version 1.20.1 fixes LKG entity propagation while preserving the v1.20.0 resilience contract. Version 1.21.0 adds execution/actionability semantics without changing the Gateway wire protocol. Version 1.22.0 adds publication/privacy hardening only. Version 1.24.0 introduced the distinct provider App packages; 1.24.1 fixes startup of the experimental DKB/TR shells. Version 1.25.0 adds local Trade Republic `DEPOTAUSZUG` statement import under the unchanged REST schema 1 contract. Version 1.26.0 adds simultaneous aggregation of multiple independently authenticated Gateway REST snapshots. Version 1.26.1 makes target/holding identity ISIN-first and reserves WKN for unambiguous fallback. Version 1.26.2 adds localized dashboard presentation and privacy-safe unavailable-source diagnostics. Version 1.26.3 is a dashboard/presentation follow-up and does not change Gateway wire or portfolio-calculation semantics. Version 1.26.4 attempted native Tile date formatting; v1.26.5 corrects the frontend boundary with additive read-only `date.*` presentation counterparts while keeping the authoritative DATE sensors and all Gateway/portfolio-calculation contracts unchanged. Version 1.26.6 fixes unavailable-source identification for reachable non-live REST Gateways. Version 1.26.7 fixes common Gateway cached-snapshot quantity persistence and HTTP validator precedence. Version 1.27.1 publishes verified private-PKI HTTPS transport; v1.27.2 fixes existing-entry Supervisor discovery eligibility; v1.27.3 fixes DKB Gateway-vs-CSV discovery identity suppression; v1.27.4 decouples Comdirect OAuth session maintenance from portfolio polling while keeping the same TLS and wire-schema contracts; v1.28.0 adds a registration-gated anonymous DKB FinTS capability probe without enabling live DKB acquisition. Version 1.28.1 changes only immutable GitHub Actions runtime pins and release metadata; provider behavior and wire contracts remain unchanged. Version 1.28.2 changes only Dependabot GitHub Actions version-update grouping and aligned release metadata; provider behavior and wire contracts remain unchanged. Version 1.29.0 changes only native reference-dashboard presentation plus aligned release metadata. Version 1.30.0 adds provider-aware local execution-policy planning while provider Gateway behavior and wire contracts remain unchanged. Version 1.31.0 corrects the canonical Robotics target, retains the former distributing holding outside current plan scope, and adds only local policy/configuration audit semantics; v1.31.1 fixes Home Assistant validation of legitimate ISIN-only outside-scope holdings. Version 1.31.2 hardens the experimental DKB FinTS registration/probe UX and bounded failure diagnostics without enabling live DKB acquisition. Version 1.32.0 adds per-source freshness observability and cross-provider diagnostic hardening. Version 1.33.0 separates provider-evidence freshness from recurring plan scheduling and adds explicit conservative evidence-kind freshness policy while preserving Gateway wire contracts; v1.33.1 corrects the remaining recurring-schedule anchor so old-but-valid source evidence cannot move the plan calendar backwards. Version 1.34.0 adds stable opaque target IDs and a structural presentation contract while retaining legacy schema-1 plan compatibility and all Gateway wire contracts; v1.34.1 fixes whole-portfolio allocation presentation and ISIN-first reference-dashboard bindings without changing those contracts. Version 1.35.0 preserves provider-owned authorized cash from every accepted Gateway, adds explicit directed funding topology in broker schema 3, and retains the same REST/health/TLS contracts and advisory-only boundary. Version 1.35.1 hardens only Comdirect session-maintenance resilience after a live-observed connection reset escaped transport classification and terminated the maintenance thread. Version 1.35.2 adds native execution-provider/funding editing and retained-cash authorization without adding transaction capability. Version 1.35.3 fixes only the missing native broker-editor menu labels. Version 1.35.4 fixes locale-sensitive cash-policy amount input and bounded Ingress validation UX. Version 1.36.0 adds only native dynamic presentation plus aligned package metadata. Version 1.36.1 fixes the live-observed dynamic allocation-card composition and compact entity-only naming without changing the presentation backend or Gateway runtime. Version 1.37.0 adds shared opt-in human-numeric Gateway validation and migrates the existing Comdirect cash-policy amount fields onto it without changing their accepted behavior. Version 1.38.0 adds Home Assistant-side copy-friendly recommendation ISIN interaction and policy-aware cash context without changing Gateway runtime. The normal release channel keeps the integration and all three provider App package versions aligned. DKB remains experimental/manual-only and non-live, with only the v1.28 anonymous FinTS capability probe; Trade Republic remains experimental and supports only the documented statement-import family.

## Getting help

Before reporting a problem:

1. confirm the installed Portfolio Architect and Home Assistant versions;
2. reproduce the issue after one integration reload;
3. review diagnostics and remove all credentials and private portfolio data;
4. check the documented known limitations and upgrade notes.

Use public issues for ordinary defects and feature requests. Use private
vulnerability reporting for issues that could expose credentials, authentication
material, account metadata, or portfolio data.

## Out of scope

The project does not provide investment advice, trade execution, order placement,
payment initiation, tax calculation, or guarantees about broker availability,
pricing, or data accuracy.
