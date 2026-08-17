# Changelog

## 1.31.0

- Retargets the active Robotics allocation from distributing `IE00BYWZ0333` / `A2ANH1` to accumulating `IE00BYZK4552` / `A2ANH0`.
- Treats an existing distributing Robotics holding as outside current plan scope: it remains visible in whole-portfolio/out-of-plan views, receives no future purchase recommendation, and does not imply an automatic sell.
- Extends exceptions schema 2 with an explicit fail-closed `superseded` audit state and retires the historical distributing-share-class exception without deleting its original decision context.
- Activates the v1.30 provider-aware broker schema in the current reference plan with an exact-instrument Trade Republic savings-plan route for the accumulating Robotics share class; no provider-wide tradability or fee is inferred.
- Preserves the legacy distributing instrument metadata so imported historical holdings remain identifiable after the target migration.
- Keeps payload schema 8, REST portfolio schema 1, Gateway health schema 6, provider acquisition, private-PKI HTTPS, LKG, DKB FinTS gating, and the advisory/no-trading boundary unchanged.

## 1.30.0

- Adds provider-aware execution routing with an opt-in `broker.yaml` schema 2 while preserving schema-1 single-broker behavior.
- Chooses the lowest-cost fresh eligible execution route across configured providers and exposes the selected provider plus fee-data date on purchase recommendations.
- Scopes accepted exceptions to an optional preferred-execution-provider assumption; a changed preferred provider reopens the exception as `review_required` while retaining the original governance decision for auditability.
- Makes savings-plan policy checks provider-aware, so a fresh compliant route can remove a fee optimisation finding without changing the instrument itself.
- Adds bounded provider-fee provenance/freshness validation, native Home Assistant provider presentation, and decision-trace detection of execution-provider changes.
- Keeps portfolio-source identity separate from execution-provider choice and adds no order placement, trading, transfer, payment or new Gateway network capability.

## 1.29.0

- Adds a native conditional **Optimisation opportunities / Optimierungsmöglichkeiten** subtitle to the policy-compliance dashboard, separating governed accepted exceptions from non-critical optimisation findings.
- Shows the existing optimisation-opportunity count as a compact native Home Assistant heading badge; the subtitle is hidden when the count is zero.
- Keeps the green mandatory-control banner, accepted-exception lifecycle tiles, four blue fee-opportunity tiles, entity IDs, machine states and policy semantics unchanged.
- Changes reference-dashboard presentation only apart from normal version/package metadata; provider acquisition, Gateway runtime, private-PKI HTTPS, schemas, calculations, LKG and the v1.28 DKB FinTS gate are unchanged.

## 1.28.2

- Groups all GitHub Actions Dependabot **version updates** into one reviewed pull request per update cycle instead of separate action-by-action PRs.
- Keeps the existing weekly GitHub Actions schedule, five-PR cap, immutable full-SHA workflow pins and Node.js 24-capable action versions unchanged.
- Does not add a Dependabot security-update group; security-update handling is not coupled to the version-update batch.
- Changes release/dependency automation only; Portfolio Architect integration, provider Gateway runtime, schemas, calculations, DKB FinTS gate, entities and dashboards are unchanged.

## 1.28.1

- Refreshes every `actions/checkout` workflow invocation from immutable v4.4.0 to immutable v7.0.1 and the validation/release `actions/setup-python` invocation from immutable v5.6.0 to immutable v7.0.0.
- Removes the remaining Portfolio Architect GitHub Actions dependency on the deprecated Node.js 20 action runtime while retaining full-SHA supply-chain pinning.
- Extends the controlled checkout refresh to HACS and hassfest workflows, which Dependabot's two-file proposal did not update.
- Adds regression coverage that requires the approved action SHAs, rejects mutable action tags and rejects the insecure Node-runtime compatibility opt-out.
- Changes no Portfolio Architect, provider, Gateway, FinTS, schema, calculation, authentication, TLS, LKG, entity or dashboard runtime behavior.

## 1.28.0

- Begins the DKB live-acquisition track with a registration-gated anonymous FinTS 3.0 BPD capability probe inside the isolated DKB Gateway App.
- Requires Portfolio Architect's own bounded FinTS product registration number and explicitly rejects reusing a library/kernel registration as the production application identity.
- Uses DKB's fixed verified-HTTPS FinTS endpoint and persists only sanitized capability metadata; raw FinTS responses are discarded.
- Treats `HIWPDS` advertisement only as bank-level research evidence; authenticated user-capability/UPD validation remains a later gate before any holdings implementation.
- Keeps DKB experimental/manual-only and non-live: no DKB username, PIN, TAN, holdings request, order, transfer, payment, debit, transaction history or portfolio snapshot is added.
- Preserves `dkb` versus `dkb_csv` provider identity/collision rules, Comdirect v1.27.4 session maintenance, Trade Republic statement import, verified HTTPS/private CA trust, bearer authentication, schemas, calculations, LKG behavior, entities and dashboards.

## 1.27.4

- Decouples Comdirect OAuth session maintenance from the independently configured portfolio refresh cadence, eliminating the timing-dependent refresh-token expiry race reproduced during live acceptance.
- Adds a provider-specific five-minute Comdirect session-maintenance loop that performs no portfolio acquisition and refreshes OAuth state only when needed.
- Latches a conclusively rejected refresh session until interactive bootstrap succeeds, avoiding repeated submission of the same rejected refresh token every scheduled cycle.
- Logs only a bounded non-secret reauthentication reason when Comdirect rejects a refresh session.
- Documents independent security-focused AI second-opinion review as an additional defense-in-depth practice in `AI_POLICY.md`.
- Keeps verified HTTPS/private CA trust, bearer authentication, portfolio polling, request-timeout behavior, schemas, calculations, LKG behavior, entities, dashboards, Trade Republic behavior, and DKB behavior unchanged.

## 1.27.3

- Fixes the residual DKB Supervisor-discovery Add card seen after successful v1.27.2 HTTPS migration when DKB CSV already represents portfolio scope.
- Separates Gateway provider identity (`dkb`) from CSV importer identity (`dkb_csv`) instead of comparing unlike provider namespaces.
- Applies the same DKB CSV collision rule to Supervisor discovery, discovered supplemental confirmation, and manual REST Gateway addition.
- Adds an executable regression using the real DKB Gateway provider ID so the previous source-string-only coverage cannot miss this mismatch again.
- Keeps verified HTTPS/private CA trust, bearer authentication, single-entry enforcement, provider acquisition, schemas, portfolio calculations, LKG behavior, entities and dashboard behavior unchanged.

## 1.27.2

- Fixes live v1.27.1 acceptance where Home Assistant never initialized the Supervisor `hassio` discovery flow for an already-configured Portfolio Architect entry because the manifest-level `single_config_entry` guard suppressed every new config flow before `async_step_hassio` could run.
- Removes the coarse manifest guard and enforces the one-entry architecture explicitly in the manual `async_step_user` path, retaining the stable unique ID as defense in depth.
- Keeps Supervisor discovery available for verified HTTP-to-HTTPS migration of the existing entry while refusing mismatched provider/network identity, changed CA trust, and automatic plaintext fallback.
- Suppresses duplicate supplemental-provider discovery prompts when that provider is already represented, including DKB CSV.
- Preserves payload schema 8, REST portfolio schema 1, Gateway health schema 6, bearer authentication, provider acquisition, portfolio calculations, entity contracts, LKG behavior, and dashboard/date behavior.

## 1.27.1

- Publishes the v1.27 verified-HTTPS milestone without changing production integration or Gateway runtime behavior from v1.27.0.
- Makes the immutable-release provider-shell Docker smoke test use the same bounded mock Supervisor, ephemeral Supervisor token and Supervisor network alias as the protected PR validation workflow.
- Verifies a real hostname-checked TLS handshake against the generated private CA during both validation and immutable publication instead of using the legacy standalone TCP-only smoke test.
- Adds a regression contract requiring the provider-shell smoke-test bodies in `validate.yml` and `release.yml` to remain identical so the two publication gates cannot drift again.
- Keeps payload schema 8, REST portfolio schema 1, Gateway health schema 6, provider acquisition, portfolio calculations, entity contracts, LKG behavior, trust migration and the read-only/no-trading boundary unchanged.

## 1.27.0

- Replaces plaintext HTTP on official Gateway App REST endpoints with certificate-verified HTTPS while retaining the dedicated bearer token as a separate authentication layer.
- Gives every official provider App a persistent per-installation ECDSA private CA and hostname-valid server certificate under App-private `/data/gateway/tls`.
- Publishes only bounded provider/endpoint identity plus the public CA certificate/fingerprint through Home Assistant Supervisor discovery; private keys and bearer tokens never enter discovery.
- Migrates matching legacy HTTP sources only after the discovered HTTPS health endpoint validates with the existing bearer token and expected provider identity; once secured, no automatic plaintext fallback is permitted.
- Refuses automatic replacement of an already-secured source when the discovered CA fingerprint changes.
- Allows newly discovered Comdirect setup and explicitly confirmed new supplemental provider addition without exposing private CA files or weakening existing provider/source collision checks.
- Preserves local-only DNS validation/pinning, payload schema 8, REST schema 1, Gateway health schema 6, provider acquisition, portfolio calculations, atomic LKG behavior, entity IDs, and the read-only/no-trading boundary.

## 1.26.7

- Fixes the cold-Gateway-restart integrity edge case discovered during v1.26.6 live acceptance: cached snapshots now preserve optional position `quantity` when reloaded.
- Makes save/load of quantity-bearing REST schema-1 snapshots byte-for-byte stable, preserving SHA-256 and ETag across normal Gateway restarts.
- Corrects HTTP conditional-request precedence so a present non-matching `If-None-Match` is never overridden by `If-Modified-Since`; changed content returns `200`, not `304`.
- Keeps fail-closed snapshot-integrity validation unchanged; it correctly detected the previous inconsistency instead of accepting altered evidence.
- Makes no Comdirect OAuth/session, PhotoTAN, refresh-cadence, provider-acquisition, portfolio-calculation, date-presentation, entity-identity, or wire-schema change.
- Preserves payload schema 8, REST schema 1, Gateway health schema 6, v1.26.6 unavailable-source diagnostics, atomic LKG behavior, and the read-only/no-trading boundary.

## 1.26.6

- Fixes the v1.26.5 live-acceptance edge case where a reachable primary Comdirect Gateway in `reauthentication_required` / Gateway-local LKG operation could make **Source unavailable** render `None`.
- Names every observed non-live REST Gateway through the existing bounded unavailable-source metadata, independent of whether Portfolio Architect has activated its separate Home Assistant LKG.
- Applies the same non-live-health invariant to additional REST Gateways while preserving existing supplemental transport/authentication/integrity and DKB CSV failure collection.
- Keeps all source labels privacy-safe and derived only from bounded provider/source IDs; no endpoint, token, account identifier, path, or provider-private state is exposed.
- Makes no Comdirect OAuth/session, refresh-cadence, provider acquisition, portfolio-calculation, date-presentation, entity-identity, or wire-schema change.
- Preserves payload schema 8, REST schema 1, Gateway health schema 6, atomic all-configured-source/LKG behavior, and the read-only/no-trading boundary.

## 1.26.5

- Corrects the v1.26.4 live-acceptance finding that Home Assistant Tile `time_format` does not locale-format `sensor` entities whose device class is `date`.
- Keeps the five established `sensor.portfolio_architect_*` `SensorDeviceClass.DATE` entities unchanged as the authoritative machine-readable dates.
- Adds five additive read-only Home Assistant `date.*` presentation counterparts that mirror the same Python `date` values so the frontend uses its native locale-aware date-domain formatter.
- Points only the affected reference-dashboard tiles at the `date.*` counterparts; state/availability conditions and portfolio logic continue to use the authoritative sensors.
- Rejects `date.set_value` for the presentation mirrors and routes each reference Tile's more-info action to its authoritative `sensor.*` counterpart, so the date domain's normal editable input UI is not exposed by the dashboard.
- Removes the ineffective v1.26.4 date-only `state_content`/`time_format` workaround and introduces no fake timestamp, timezone conversion, locale-specific template, or hard-coded date string.
- Preserves refresh-schedule timestamp formatting, payload schema 8, REST schema 1, Gateway health schema 6, all existing entity IDs, provider acquisition/cash/LKG behavior, and the read-only/no-trading boundary.

## 1.26.4

- Makes all date-only reference-dashboard tiles use Home Assistant's native locale-aware Tile date rendering instead of showing raw ISO `YYYY-MM-DD` states.
- Applies the same generic `date` / `short` Tile formatting to Scheduled execution, Next plan review, Last decision, Next/overdue review in both English and German dashboard variants.
- Keeps the underlying date entities as native `SensorDeviceClass.DATE` values and adds no locale-specific date attributes, templates, or hard-coded format strings.
- Keeps refresh-schedule timestamps on the existing native `datetime` / `short` Tile rendering, intentionally without seconds.
- Preserves v1.26.3 dashboard/policy polish, v1.26.2 source-outage diagnostics, v1.26.1 ISIN-first identity, v1.26 atomic multi-Gateway/LKG behavior, payload schema 8, REST schema 1, health schema 6, existing entity IDs, and the read-only/no-trading boundary.

## 1.26.3

- Fixes the remaining German reference-dashboard unavailable-state edge case without changing the underlying actionable entity availability contract: the always-available actionability sensor now supplies bounded German presentation proxies for the Allocated and Purchases tiles.
- Removes the low-value aggregate **Checks** and **Opportunities** counters from the primary policy dashboard while retaining their native entities for diagnostics, automations, and API consumers.
- Reorders the policy section around the accepted-exception lifecycle: Exceptions → Robotics exception, then Last decision → Next/overdue review, followed by the concrete optimisation opportunity tiles.
- Uses precise English/German exception lifecycle labels and keeps conditional policy error/warning tiles available when findings require attention.
- Preserves v1.26.2 source-outage diagnostics, v1.26.1 ISIN-first identity, v1.26 atomic multi-Gateway/LKG behavior, payload schema 8, REST schema 1, health schema 6, existing entity IDs, and the read-only/no-trading boundary.

## 1.26.2

- Completes the German reference-dashboard presentation layer so machine-readable entity states remain stable while German dashboard state values render explicitly in German, independent of the Home Assistant frontend language.
- Adds privacy-safe unavailable-source metadata (`unavailable_source_count`, bounded source IDs and English/German summaries) so the Source unavailable tile identifies which configured source instances are blocking a live aggregate.
- Collects multiple additional-Gateway availability failures in one refresh while preserving v1.26 atomic aggregation: any configured source failure retains the matching complete Home Assistant LKG rather than partially aggregating successful providers.
- Adds safe DKB CSV source-instance failure labels without exposing configured file paths.
- Fixes the Gateway attention-reason presentation for supplemental-source outages by declaring/translating `supplemental_source_unavailable` instead of rendering `None`.
- Keeps payload schema 8, REST portfolio schema 1, Gateway health schema 6, machine-readable entity states/IDs, ISIN-first identity, provider acquisition, authorized-cash semantics and the read-only/no-trading boundary unchanged.

## 1.26.1

- Fixes v1.26.0 live acceptance for Trade Republic holdings whose provider-neutral REST snapshot carries an ISIN but no WKN.
- Makes ISIN the canonical instrument identity for target matching and cross-source aggregation; WKN is used only as a fallback when ISIN is unavailable.
- Treats WKN as secondary consistency evidence when an ISIN is present and fails closed on contradictory or ambiguous ISIN/WKN mappings instead of guessing.
- Stops the REST adapter from mislabelling an ISIN-valued provider identifier as a WKN.
- Adds regression coverage using the real Trade Republic REST identity shape (`identifier == ISIN`, no WKN) and requires the synthetic three-provider portfolio to reach 7/7 target coverage.
- Preserves v1.26.0 multi-Gateway configuration, provider counts/provenance, atomic LKG behavior, payload schema 8, REST schema 1, health schema 6, entity IDs and the read-only/no-trading boundary.

## 1.26.0

- Adds simultaneous aggregation of multiple independent provider Gateway REST snapshots while preserving the existing primary REST configuration.
- Validates every additional Gateway with local-only transport, bearer authentication, health schema 6 provider identity, live snapshot, and matching integrity metadata before saving it.
- Makes multi-Gateway refresh atomic: a configured provider outage or integrity failure retains the previous complete Home Assistant last-known-good aggregate rather than silently dropping that provider.
- Adds distinct `provider_count` / `provider_ids` metadata alongside source-instance count and existing per-position provenance.
- Updates the reference dashboard Source provider tile to show a compact distinct-provider summary such as `Multi-source portfolio · 3 providers`.
- Changes the functional Trade Republic App to `boot: auto` so an accepted statement snapshot remains available to a configured Portfolio Architect consumer across Home Assistant restarts.
- Preserves payload schema 8, REST portfolio schema 1, Gateway health schema 6, existing entity IDs, Comdirect cash semantics, and the no-trading/write boundary.

## 1.25.0

- Adds local, admin-only import of the supported German Trade Republic `DEPOTAUSZUG` text-PDF statement family inside the separate Trade Republic Gateway App.
- Parses uploaded PDFs in memory, persists only the validated provider-neutral holdings snapshot, and never stores the original statement document.
- Fails closed on encrypted, image-only/scanned, malformed, unsupported, ambiguous, future-dated, count-mismatched, or total-mismatched statements.
- Keeps account-holder, address, depot/account, tax, and other attribution fields out of the REST payload, diagnostics, logs, public fixtures, and release artifacts.
- Pins the Trade Republic App's PDF parser dependency (`pypdf 6.15.0`) by exact wheel hash; Comdirect, DKB, and the standalone Gateway remain dependency-free from that provider-specific parser.
- Preserves payload schema 8, REST portfolio schema 1, Gateway health schema 6, Comdirect cash/LKG/actionability behavior, provider App identities, and the no-trading/write boundary.

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
