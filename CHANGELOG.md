# Changelog

## 1.24.1

- Fixes DKB and Trade Republic provider-shell startup after v1.24.0 live acceptance exposed a runtime import of the Comdirect-only `config.py` module from the reduced shell package.
- Moves the `GatewayConfig` import in the common server behind `TYPE_CHECKING`; runtime server state remains based on provider-neutral `ServerConfig`.
- Adds isolated-package regression coverage that imports the exact DKB/TR runtime subset with `config.py` absent.
- Makes DKB/TR Docker builds import the real `pending_app` startup module instead of only the package root.
- Adds protected container smoke tests that require both experimental shells to remain running and listen on their Ingress and private REST ports before merge/publication.
- Preserves Comdirect behavior, payload schema 8, REST portfolio schema 1, Gateway health schema 6, provider identities, read-only semantics, and the v1.24 provider-App split.

## 1.24.0

- Introduces a provider-neutral `PortfolioProvider` runtime contract for the common hardened Gateway server.
- Removes the common server's direct type/import dependency on `ComdirectClient`; the released provider remains Comdirect.
- Adds Gateway health schema 6 with bounded non-secret `provider_id` while retaining health schemas 1 through 5 unchanged.
- Makes the Home Assistant REST client negotiate health schema 6 with explicit v5→v1 fallbacks for older supported Gateways.
- Renames the visible existing App to **Portfolio Architect Gateway — Comdirect** while retaining the established `portfolio_architect_gateway` slug and App-private state.
- Documents reserved future App identities for DKB and Trade Republic without shipping non-functional provider runtimes.
- Preserves payload schema 8, REST schema 1, entity IDs, calculations, authorized-cash semantics, LKG/actionability behavior, and the v1.22 publication/privacy controls.

## 1.22.0

- Makes publication privacy hygiene a fail-closed release invariant.
- Adds Portfolio Architect-specific source and release-artifact checks for attributable account material, raw broker documents, unapproved exports, unexpected images, valid IBANs, key material, and non-synthetic provider identity literals.
- Adds digest-pinned Gitleaks v8.30.0 scanning of the tracked tree, complete Git patch history, and built release contents in protected validation and immutable-release workflows.
- Requires full Git history in the validation workflow and runs the secret/privacy gates before release attestation or publication.
- Rejects source symlinks and excludes local virtual-environment directories from release staging.
- Clarifies that copied/imported Lovelace dashboards are user-owned and are not overwritten by HACS or Portfolio Architect.
- Adds the roadmap for provider-separated Comdirect, DKB, and Trade Republic Gateway Apps followed by Trade Republic statement-document import.
- Preserves payload schema 8, REST schema 1, Gateway health schema 5, entity IDs, v1.21 actionability, authorized-cash semantics, LKG behavior, calculations, and read-only Gateway banking behavior.

## 1.21.0

- Separates scheduled execution timing from current recommendation actionability without changing the existing `planned_execution` entity ID.
- Adds `sensor.portfolio_architect_plan_actionability` with bounded states for scheduled, actionable-now, overdue-but-actionable, not-ready, and non-actionable recommendations.
- Treats a past scheduled date as planning context rather than evidence that a recommendation expired or that any trade occurred.
- Adds schedule relation, evaluation timestamp, and actionability reason attributes for explainable Home Assistant automations and more-info views.
- Updates the reference dashboards to show **Scheduled execution**, **Actionability**, and **Last evaluated** separately.
- Clarifies v1.20 freshness semantics as **Snapshot freshness / Within freshness window**, avoiding the misleading implication that a reachable live bank source is required for a retained trusted snapshot to be fresh enough.
- Preserves payload schema 8, REST schema 1, Gateway health schema 5, existing entity IDs/unique IDs, authorized-cash behavior, LKG safety, and the read-only/no-transaction-inference boundary.

## 1.20.1

- Fixes graceful-degradation entity propagation when the coordinator republishes the same trusted `PortfolioData` with changed LKG, health, or actionability metadata.
- Ensures LKG entry immediately updates health entities and makes authorized cash, recommendations, fees, outlay, and other actionability-sensitive entities unavailable while informational holdings remain visible.
- Makes coordinator listener notifications authoritative for each completed update cycle instead of suppressing them when only out-of-band coordinator metadata changed.
- Keeps integrity Repairs tied to current integrity evidence so an unrelated transport or calculation fallback does not republish a stale integrity-failure reason.
- Adds regression coverage that a reauthentication-required Gateway continues to expose integrity metadata for its cached snapshot.
- Preserves payload schema 8, REST schema 1, Gateway health schema 5, entity IDs, unique IDs, authorized-cash semantics, and v1.20.0 LKG retention rules.

## 1.20.0

- Adds bounded graceful degradation so a previously validated REST portfolio remains informationally available during longer live-source outages instead of collapsing the whole portfolio to unavailable.
- Separates trusted informational data from actionable planning: cached or degraded holdings, allocation, and policy remain visible, while authorized cash and new purchase recommendations require a fresh, healthy, live source.
- Rejects timestamp-regressed or integrity-inconsistent incoming snapshots without discarding the previously accepted last-known-good calculation.
- Fixes false `refresh_overdue` alarms by requiring a health observation obtained after the missed deadline plus grace; an old schedule timestamp can no longer become failure evidence by itself.
- Derives snapshot age and retention countdown locally from the accepted snapshot timestamp and updates their entities on the existing minute tick.
- Adds transparent AI-assisted development disclosure and `AI_POLICY.md` while retaining human-controlled branch, merge, tag, and release decisions.
- Preserves payload schema 8, REST schema 1, Gateway health schema 5, entity IDs, unique IDs, authorized-cash semantics, and the read-only Gateway surface.

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
