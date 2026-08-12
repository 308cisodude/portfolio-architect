# Changelog

## 1.19.1

- Fixes the Gateway Ingress transition from `capped` to `all_available` when a browser still submits the previous cap value.
- Makes server-side policy parsing authoritative: `all_available` canonicalizes any irrelevant submitted cap to `None` before persistence.
- Keeps persisted-state validation strict, so malformed on-disk `all_available` policies that contain a cap are still rejected.
- Improves the Ingress form UX by clearing/disabling the cap field outside capped mode without relying on client-side behavior for correctness.
- Preserves authorized-cash calculations, REST schema 1, payload schema 8, Gateway health schema 5, entity IDs, and allocation semantics.

## 1.19.0

- Adds Gateway-owned investment-cash authorization with `all_available` and fail-closed `capped` policies.
- Separates bank-reported account balance, eligible non-borrowed cash, and the amount Portfolio Architect is authorized to allocate.
- Extends REST schema 1 additively with bounded `investment_cash` metadata while retaining `investment_reserve.available_eur` as the authorized compatibility value.
- Renames the existing reserve entity display name to **Authorized investment cash** without changing its entity ID or unique ID.
- Preserves compatibility with older supported Gateways and keeps DKB supplemental CSV behavior unchanged.
- Excludes the historical experimental `v1.19.0-rc2` brokerage diagnostics from the stable release.

## 1.18.2

- Removes invalid `measurement` state classes from advisory monetary sensors for Home Assistant compatibility.
- Preserves monetary device classes, EUR units, entity IDs, unique IDs, values, and calculation semantics.
- Adds a regression contract that prevents monetary sensors from acquiring the invalid `measurement` state class again.
- Keeps valid measurement metadata on non-monetary sensors unchanged.
- Aligns Gateway App package versioning; Gateway runtime and REST/health contracts are unchanged.

## 1.18.1

- Adds provider-supplied holding-quantity sensors without inferring transaction history.
- Retains DKB quantities and propagates optional Comdirect quantities through REST schema 1.
- Keeps quantity unavailable when any aggregated source lacks quantity evidence.
- Renames the portfolio-value and allocation dashboard headings for clarity.
- Preserves recommendation, reserve, policy, target-corridor, and decision-trace behavior.

## 1.18.0

- Adds a private two-evaluation Plan Delta & Decision Trace.
- Adds `sensor.portfolio_architect_plan_change` with bounded translated states and stable per-position reason codes.
- Suppresses drift-only changes below 0.10 pp and non-zero purchase changes below EUR 1.00 while always reporting status transitions and additions/removals.
- Prevents REST last-known-good replay from advancing the decision trace.
- Adds a native bilingual conditional dashboard tile and privacy-conscious diagnostics.
- Protects the private history with canonical SHA-256 validation and excludes detailed trace attributes from recorder history.
- Preserves payload schema 8, REST schema 1, Gateway health schema 5, allocation, policy, execution, and existing entity contracts.

## 1.17.2

- Fixes the HACS release asset so integration files are stored directly at the ZIP root.
- Retains the wrapped `custom_components/portfolio_architect/` layout for the manual Home Assistant drop-in.
- Adds release verification for channel-specific archive roots and complete payload equivalence after prefix normalization.
- Adds a regression test that rejects the v1.17.1 nested-HACS packaging failure.
- Preserves the v1.17.1 runtime, security hardening, portfolio behavior, entities, dashboards, and Gateway protocols.

## 1.17.1

- Supersedes the unpublished v1.17.0 publication candidate.
- Pins every reusable GitHub Action to a full 40-character commit SHA.
- Runs the HACS and hassfest validators from immutable GHCR image digests because
  their upstream wrapper actions currently delegate to mutable container tags.
- Adds fail-closed workflow checks that reject mutable action refs and container
  image tags.
- Pins validation and release jobs to Ubuntu 24.04 and Python 3.14.6, and installs
  every direct and transitive Python validation dependency from a version- and
  SHA-256-locked wheel list with hash enforcement and no dependency resolution;
  the set uses Pygments 2.20.0 rather than the vulnerable 2.19.2 release.
- Removes the local REST DNS validation/connection race by resolving once,
  validating every returned address, and binding the request to that exact
  address set while preserving the original Host header, TLS SNI, and certificate
  name validation.
- Disables redirects, environment proxies, and cookie persistence for authenticated
  local REST requests.
- Strengthens generated CODEOWNERS coverage for workflows, dependency automation,
  publication tooling, the integration, and both Gateway distributions; the
  inactive example file is removed after repository configuration.
- Adds executable regression tests for pinned DNS transport and immutable
  publication dependencies.
- Preserves the v1.16.3 portfolio calculation, entity, dashboard, fee, and Gateway
  protocol contracts.

Historical release details are retained in `docs/UPGRADE-*.md` and the source
history.
