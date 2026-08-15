# Support policy

Portfolio Architect is a community-maintained Home Assistant custom integration.
It is not maintained, reviewed, or supported by Home Assistant, Comdirect, DKB,
or any execution venue.

## Supported versions

Security and correctness fixes are provided for:

- the current stable Portfolio Architect release; and
- the immediately preceding stable release while a documented upgrade path exists.

The Home Assistant support floor for the 1.27.x release line is **2026.7.0**.
The project targets the current and immediately previous monthly Home Assistant
release, subject to automated compatibility checks. Beta releases receive
best-effort compatibility only.

Gateway App versions 1.16.1 and later remain compatible with Portfolio Architect
1.27.1 through the legacy reserve contract. Gateway App 1.19.0 or newer is required
for configurable authorized-cash policy metadata; 1.19.1 or newer contains the
corrected capped-to-all-available Ingress transition. Version 1.20.1 fixes LKG entity propagation while preserving the v1.20.0 resilience contract. Version 1.21.0 adds execution/actionability semantics without changing the Gateway wire protocol. Version 1.22.0 adds publication/privacy hardening only. Version 1.24.0 introduced the distinct provider App packages; 1.24.1 fixes startup of the experimental DKB/TR shells. Version 1.25.0 adds local Trade Republic `DEPOTAUSZUG` statement import under the unchanged REST schema 1 contract. Version 1.26.0 adds simultaneous aggregation of multiple independently authenticated Gateway REST snapshots. Version 1.26.1 makes target/holding identity ISIN-first and reserves WKN for unambiguous fallback. Version 1.26.2 adds localized dashboard presentation and privacy-safe unavailable-source diagnostics. Version 1.26.3 is a dashboard/presentation follow-up and does not change Gateway wire or portfolio-calculation semantics. Version 1.26.4 attempted native Tile date formatting; v1.26.5 corrects the frontend boundary with additive read-only `date.*` presentation counterparts while keeping the authoritative DATE sensors and all Gateway/portfolio-calculation contracts unchanged. Version 1.26.6 fixes unavailable-source identification for reachable non-live REST Gateways. Version 1.26.7 fixes common Gateway cached-snapshot quantity persistence and HTTP validator precedence. Version 1.27.1 adds verified private-PKI HTTPS transport with Supervisor trust discovery and fail-closed migration while keeping both wire schemas and provider acquisition unchanged. The normal release channel keeps the integration and all three provider App package versions aligned. DKB remains an experimental non-live provider shell; Trade Republic remains experimental and supports only the documented statement-import family.

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
