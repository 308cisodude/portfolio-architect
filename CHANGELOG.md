# Changelog

## 1.49.0

- Retires the completed Home Assistant-side Comdirect `comdirect_csv` parser and one-release exact-equivalence migration bridge after the v1.48 Gateway cut-over was live-proven.
- Adds fail-closed config-entry schema 11: a still-active legacy Comdirect CSV source must complete the v1.48.2 verified Gateway migration before upgrading and is never silently reinterpreted or discarded.
- Removes the current `comdirect_csv` source-provider/config-flow/translation/icon surfaces while keeping the provider-neutral mapped generic CSV adapter.
- Leaves Comdirect Gateway `live_api`/`csv` acquisition, DKB CSV, Trade Republic PDF acquisition, v1.48 freshness policy, planner economics and all wire/security contracts unchanged.

## 1.48.2

- preserve health-schema-7 `acquisition_mode` in the coordinator source summaries used by live freshness evaluation instead of overwriting it with acquisition-neutral aggregation metadata
- re-annotate existing source summaries from fresh Gateway health on `304 Not Modified` refreshes so App upgrades or deliberate acquisition-mode changes do not require a holdings change to take effect
- keep live and Home Assistant LKG source-summary acquisition metadata consistent while retaining conservative fallback when an acquisition mode is absent or unknown
- leave v1.48.1 freshness thresholds/defaults, provider acquisition, no-fallback semantics, planner economics and wire/security contracts unchanged

## 1.48.1

- classify health-schema-7 `acquisition_mode=csv` as static CSV evidence and `pdf` as imported-statement evidence instead of inheriting the live Gateway window
- add cadence-aware unconfigured static defaults: 5 days for weekly plans and 14 days for monthly-or-slower plans, while live/unknown Gateway evidence remains 24 hours
- preserve every explicitly configured evidence-kind threshold and the pre-v1.33 global compatibility threshold
- keep holdings and provider cash on independent evidence clocks; provider acquisition and no-fallback semantics are unchanged

## 1.48.0

- Moves Comdirect provider-specific depot CSV parsing into the Comdirect Gateway and adds a complete explicit static mode with independent holdings and cash CSV evidence.
- Adds strict `live_api`/`csv` arbitration with no silent cross-mode fallback; CSV mode disables automatic API acquisition and OAuth/session maintenance while explicit PhotoTAN preparation remains possible.
- Adds fail-closed legacy PA-side Comdirect CSV migration after verified-HTTPS, health-schema-7, explicit-mode, integrity and exact canonical holdings checks.
- Adds Gateway health schema 7 with bounded `acquisition_mode`; schemas 1–6 and REST portfolio schema 1 remain compatible.
- Makes live/static acquisition optically distinct in Comdirect, DKB and Trade Republic Ingress pages without changing DKB/TR acquisition semantics or the advisory-only boundary.

## 1.47.0

- Adds independent DKB Girokonto `Umsatzliste` CSV cash evidence inside the DKB Gateway beside the established depot-CSV holdings acquisition.
- Persists only normalized balance/date evidence; account identifiers, transaction rows, counterparties, references and raw cash CSV bytes remain transient.
- Keeps DKB holdings and cash timestamps independent; DKB cash uses the imported-statement freshness policy while DKB holdings remain a Gateway snapshot.
- Clamps zero/negative account balances to EUR 0 eligible/authorized investment cash and never infers overdraft or credit availability.
- Preserves REST schema 1, health schema 6, FinTS isolation, Comdirect/TR acquisition, planner economics, private-PKI transport and dashboard presentation.

## 1.46.0

- Retires the live-proven Home Assistant-side DKB `dkb_csv` parser, supplemental-path source model and v1.45 discovery migration bridge; DKB CSV acquisition now lives only inside the DKB Gateway.
- Adds fail-closed config-entry schema 10: an installation with active legacy DKB CSV configuration must complete the v1.45.1 Gateway cut-over before upgrading, preventing silent source loss.
- Removes the temporary DKB migration-only REST endpoint after the bridge is retired while keeping normal DKB Gateway CSV acquisition, freshness enforcement and anonymous FinTS probing unchanged.
- Preserves portfolio/planner economics, cash routing, Comdirect/TR acquisition, verified private-PKI transport, LKG/source atomicity, wire schemas and dashboard presentation.

## 1.45.1

- Fixes v1.45.0 legacy DKB CSV migration when the exact comparison export is older than the DKB Gateway's normal cached-snapshot serving horizon.
- Adds a DKB-only, bearer-authenticated, verified-HTTPS read-only migration-snapshot endpoint that can expose only the already-normalized canonical snapshot for exact equivalence checking without making it available to normal runtime.
- Makes expired Gateway health documents schema-consistent by withholding available-snapshot timestamp/age/integrity metadata while `snapshot_available` is false.
- Preserves exact atomic source cut-over, normal seven-day DKB runtime freshness, private-PKI/DNS pinning, FinTS isolation, portfolio calculations and the advisory-only boundary.

## 1.45.0

- Moves active DKB depot-CSV acquisition into the DKB Gateway App with strict bounded parsing, transient-only depot identity and canonical private snapshot persistence.
- Adds an exact verified-HTTPS migration gate from legacy HA-side `dkb_csv` sources to `provider_id: dkb`; one atomic config-entry update removes the old paths only after holdings and conservative source timestamp match exactly.
- Auto-starts the DKB App while retaining its experimental stage; the anonymous FinTS capability probe remains separate and no login/PIN/TAN, authenticated holdings, trading or money-movement capability is added.
- Preserves payload/REST/health/presentation/broker schemas, single-entry architecture, Comdirect/TR acquisition, planner economics, v1.44 Configure UX and the advisory-only boundary.

## 1.44.0

- Audits every native Configure menu and requires complete English/German labels plus translated destination titles, including the live-observed blank Edit funding transfer row.
- Adds non-editable identity context above every selected-object edit form: execution provider, savings-plan provider/ISIN route, and exact directed funding-transfer edge; the already-contextualized plan-instrument editor remains unchanged.
- Preserves v1.43 route-level evidence semantics, route economics, provider acquisition, wire/security schemas, v1.42 execution-path/dashboard presentation and the advisory/no-money-movement boundary; no broker or dashboard migration is required.

## 1.43.0

- Adds optional per-savings-plan-route `source` + `as_of` provenance and independent freshness using the existing broker fee-data age window, while legacy routes continue to inherit provider-level evidence unchanged.
- Enhances the existing native savings-plan route editor to create/refresh explicit route evidence and adds native editing for exact directed funding-transfer fee, settlement-time and evidence fields without changing edge identity.
- Preserves broker schemas 1/2/3, route economics, provider acquisition, v1.42 execution-path presentation, verified private-PKI transport and the advisory/no-money-movement boundary; no dashboard migration is required.

## 1.42.0

- Adds a bounded normalized Home Assistant execution-path entity that turns the already-decided actionable plan into ordered local-cash, funding-transfer and purchase presentation steps without rerunning route selection.
- Adds English/German plain-text and Markdown rendering plus a native bilingual **Execution path / Ausführungsweg** dashboard block whose Jinja only reads the integration-owned presentation attribute.
- Preserves payload/REST/health/presentation/broker schemas, v1.41.1 provider-local-cash routing, provider acquisition, verified private-PKI transport and the advisory/no-money-movement boundary; users of the supplied dashboard should bulk-replace its complete YAML.

## 1.41.1

- Fixes the live-proven zero-fee/zero-day provider-funding tie where a Trade Republic purchase could be funded from Comdirect even though sufficient fresh Trade Republic local cash was already available.
- Keeps cost, settlement time, explicit provider priority, order amount and fees ahead of the new tie-break, then prefers `funding_transfer_required: false` before arbitrary route/provider identifiers when those existing economics are otherwise equal.
- Adds executable regression coverage reproducing the exact local-cash-versus-Comdirect-transfer parity case while preserving v1.41.0 Trade Republic KONTOAUSZUG acquisition, evidence freshness, schemas, provider runtimes and the advisory/no-money-movement boundary.

## 1.41.0

- Adds a separate strict Trade Republic `KONTOAUSZUG` text-PDF importer for provider-scoped cash while preserving the established `DEPOTAUSZUG` holdings importer as an independent evidence family.
- Reconciles Cashkonto arithmetic and trust-account/QMMF custody totals before accepting cash, persists only bounded normalized private cash state, and never stores raw PDFs, transaction rows, counterparties, account identifiers, names or addresses.
- Keeps holdings and cash timestamps independent through REST schema 1 and freshness-gates provider cash separately using the existing imported-statement threshold so fresh cash cannot refresh stale holdings and fresh holdings cannot refresh stale cash.
- Preserves verified private-PKI transport, provider isolation, broker/funding semantics, dashboard presentation and the advisory/no-money-movement boundary; no unofficial Trade Republic API is introduced.

## 1.40.1

- Fixes the native savings-plan Add/Edit form HTTP 400 by raising its percentage NumberSelector step from the Home Assistant-invalid `0.0001` to the supported `0.001` floor, without changing typed fee semantics.
- Audits the full Portfolio Architect Configure surface against Home Assistant Core 2026.8.1 selector contracts and adds executable regression coverage for every numeric selector step, selector mode/type, rendered options-flow translation and menu destination.
- Replaces broker evidence-date free text with native DateSelector controls; new evidence defaults to the current Home Assistant-local date, existing provider evidence stays preselected on edit, and broker validation uses the same local evaluation date across load/mutate/write.
- Adds bounded field-level errors for duplicate execution providers, savings-plan routes and directed funding transfers while preserving all v1.40.0 funding/evidence semantics, provider runtimes, schemas, dashboard presentation and the advisory/no-money-movement boundary.

## 1.40.0

- Adds optional evidence provenance (`source` + `as_of`) to existing broker-schema-3 directed funding-transfer edges while preserving legacy schema-3 edges for backward compatibility.
- Native broker editing now creates evidence-backed transfer edges and requires the operator to record both evidence source and evidence date alongside verified fee and conservative settlement time.
- Evidence-backed transfer edges use the existing `fee_data_max_age_days` freshness window; stale edges remain valid configuration evidence but fail closed for route selection until refreshed, and future/partial evidence is rejected.
- Preserves provider-scoped cash ownership, explicit one-way topology, cost-first route ranking, REST schema 1, Gateway health schema 6, private-PKI HTTPS, provider acquisition, dashboard presentation and the advisory/no-money-movement boundary.

## 1.39.0

- Replaces the two bounded current/target allocation entity-filter lists with paired native Conditional + Tile cards for all 32 generic presentation slots, restoring a colourful position-identity view without hard-coded instrument inventory.
- Gives each current/target slot pair the same deterministic native colour and a 0–100% Tile `bar-gauge`; current visibility is keyed to target membership so a configured-but-missing target remains visible at 0%.
- Preserves the live-accepted v1.38.1 amber/green/red signed drift Tiles unchanged, including -100…+100 pp gauges and tap-through to bounded allocation explanations.
- Preserves v1.38.0 policy-aware cash context and copy-friendly ISIN interaction, presentation schema 2, provider runtimes, Gateway wire/security contracts, funding/cash mathematics and the advisory/no-trading boundary.

## 1.38.1

- Restores native dynamic allocation-drift visualization for all 32 bounded generic target presentation slots without reintroducing an instrument-specific dashboard inventory.
- Uses only core Home Assistant Conditional and Tile cards: underweight slots render amber, on-target slots green, and overweight slots red, with the Tile-native signed `bar-gauge` bounded from -100 to +100 percentage points.
- Keeps instrument names dynamic and makes each visible drift tile open the matching bounded allocation explanation on tap.
- Preserves the v1.38.0 policy-aware cash context and copy-friendly recommendation ISIN interaction, presentation schema 2, provider runtimes, Gateway wire/security contracts, funding/cash mathematics and the advisory/no-trading boundary.

## 1.38.0

- Adds native dashboard cash-policy context so **Authorized investment cash** shows total available cash and the amount excluded by policy, while **Cash after recommended purchases** also shows planned cash outlay.
- Restores copy-friendly recommendation interaction without hard-coded instrument inventory: tapping a dynamic recommended-purchase row opens that slot's ISIN entity, while holding the row opens the existing bounded purchase explanation.
- Keeps the v1.36 presentation-slot backend, presentation schema 2, dynamic candidate bounds and native-only dashboard architecture unchanged; no custom frontend dependency is added.
- Preserves v1.37 shared human-input validation, provider runtimes, payload/REST/health/broker schemas, funding/cash mathematics, private-PKI transport and the advisory/no-trading boundary.

## 1.37.0

- Adds shared, opt-in Gateway human-numeric validation primitives for EUR/money, percentages, quantities and bounded integers with canonical typed output and bounded non-reflective errors.
- Migrates the existing Comdirect capped/retained cash amount fields onto the shared EUR primitive while preserving every live-proven v1.35.4 locale form, canonical private persistence and previous-state-on-error behavior.
- Rejects unsafe/ambiguous numeric syntax rather than guessing; protocol identifiers, registrations, credentials, tokens and exact IDs stay on provider-specific validation paths and bypass locale numeric normalization.
- Mirrors the helper into all provider App build contexts for future opt-in use without changing DKB/TR provider behavior, wire schemas, presentation schema 2, funding/cash mathematics, private-PKI transport or the advisory/no-trading boundary.

## 1.36.1

- Fixes the live-observed native-dashboard incompatibility where `entity-filter` correctly selected dynamic allocation slots but a nested Distribution card remained empty.
- Renders the three dynamic allocation surfaces through core Entities cards while preserving the same positive-value filters, bounded slot inventories and presentation schema 2 backend contract.
- Uses Home Assistant structured entity-only names for dynamic presentation candidates so instrument labels no longer inherit the `Portfolio Architect` device prefix; no instrument names are hard-coded back into YAML.
- Preserves provider runtimes, v1.35.4 Comdirect cash-input normalization, retained cash/funding, broker semantics, Gateway wire/security contracts and the advisory/no-trading boundary.

## 1.36.0

- Completes the native dynamic portfolio-presentation milestone with bounded diagnostic presentation-slot adapters for configured targets, outside-scope holdings and active policy findings.
- Upgrades the structural presentation model to schema 2 with explicit one-based slot metadata while preserving opaque target IDs and accepted holding position IDs as stable portfolio identity.
- Replaces instrument-specific reference-dashboard inventories with native Home Assistant `entity-filter` cards feeding core Entities, Glance and Distribution cards; no `auto-entities`, card-mod, JavaScript or custom-card dependency is added.
- Keeps dashboard ownership opt-in: HACS/integration updates never overwrite imported or personalized Lovelace YAML.
- Preserves payload schema 8, REST portfolio schema 1, Gateway health schema 6, broker schemas 1/2/3, provider-scoped funding/cash, v1.35.4 cash-input normalization, provider acquisition, verified HTTPS and advisory/no-trading boundaries.

## 1.35.4

- Accepts common human EUR amount formats in the Comdirect cash-authorization form, including decimal comma/dot and validated dot/comma/space/apostrophe thousands grouping, while keeping private persisted state canonical and locale-neutral.
- Fixes the live-observed `1024,00` retained-cash submission failure; the same tolerant parser applies to both **Cap authorized cash** and **Keep cash reserve**.
- Replaces the generic browser HTTP 400 for an invalid cash amount with a bounded relative Ingress redirect and fixed non-sensitive validation guidance; invalid input cannot overwrite the last valid private policy.
- Preserves all cash-policy mathematics, REST/health schemas, provider-scoped funding, broker semantics, Comdirect OAuth/session behavior, verified HTTPS and the advisory/no-trading boundary.

## 1.35.3

- Restores visible English/German labels for every list-based menu in the native Execution providers & funding editor introduced in v1.35.2.
- Adds regression coverage that derives each emitted broker-editor menu option from config_flow.py and requires a non-empty translation matching the destination-step title in both languages.
- Preserves v1.35.2 broker editing, route economics, tie-break/promotional semantics and Keep cash reserve behavior unchanged.
- Preserves Gateway wire schemas, provider runtimes, verified HTTPS and the advisory/no-trading boundary; provider Apps receive version alignment only.

## 1.35.2

- Adds a native validated Home Assistant editor for provider-aware `broker.yaml` schemas 2/3, including provider evidence, savings-plan routes and exact directed funding topology.
- Presents provider `priority` as an optional tie-break preference while preserving cost-first and settlement-time-second routing; existing advanced numeric priority is preserved when its preference tier is unchanged.
- Validates savings-plan `promotional` as boolean descriptive/provenance metadata only; it never participates in route economics.
- Adds provider-owned **Keep cash reserve** (`retain`) authorization: `max(eligible - retain_eur, 0)`, with backward-compatible private policy-state loading.
- Preserves v1.35.1 Comdirect maintenance resilience, v1.35.0 funding semantics, verified HTTPS and the advisory/no-trading boundary.

## 1.35.1

- Classifies direct Comdirect `ConnectionError` transport failures, including the live-observed `ConnectionResetError`, as bounded retryable `RemoteApiError` failures instead of allowing them to escape the OAuth/session layer.
- Adds defense-in-depth containment around each long-lived Comdirect session-maintenance iteration so an unexpected single failure cannot terminate the maintenance worker; unexpected diagnostics log only the exception type.
- Corrects the two remaining German accumulating-Robotics allocation-chart labels to `Robotik · Thes.`.
- Preserves v1.35.0 provider-scoped funding, broker schema 3, REST/health/TLS contracts, provider acquisition behavior and the advisory/no-trading boundary.

## 1.35.0

- Preserves authorized investment cash as provider-scoped evidence across all accepted REST Gateways instead of collapsing supplemental-provider cash into a global reserve.
- Adds opt-in broker schema 3 with explicit directed funding-transfer edges, bounded transfer fees and settlement business days; reverse transferability is never inferred.
- Chooses funding source and execution route together, includes transfer fees in route economics, debits only the cash pool actually used, and emits a bounded advisory aggregate transfer plan.
- Keeps schemas 1/2 behavior, REST portfolio schema 1, Gateway health schema 6, private-PKI transport and the no-transfer/no-trading boundary unchanged.
- Disambiguates accumulating Robotics as `Robotics · Acc` / `Robotik · Thes.` and adds exact raw DKB capability-probe response-body SHA-256/byte evidence without retaining response bytes.

## 1.34.1

- Fixes whole-portfolio distribution after the v1.34 opaque-target migration: every configured target now owns its established whole-portfolio allocation entity even when currently missing, so a missing target renders as 0% rather than an unresolved entity reference.
- Migrates reference-dashboard outside-scope distribution bindings from obsolete WKN-era holding IDs to the established ISIN-first `holding_<identity>` IDs.
- Keeps the intentionally static outside-scope detail Tile inventory unchanged pending the later dynamic native-dashboard milestone; the v1.34 presentation model remains the complete current-state inventory.
- Preserves target IDs, portfolio calculations, source freshness, scheduling, provider runtimes, wire schemas, cash/execution behavior and the advisory/no-trading boundary.

## 1.34.0

- Adds portfolio schema 2 with explicit opaque `target_id` values generated from 128 random bits while retaining schema-1 legacy `id` compatibility.
- Keeps target-role identity independent from ISIN, WKN, display name, list order and weight; the native plan editor generates target IDs automatically and keys instrument candidates by ISIN.
- Re-adding the same instrument after deleting a target creates a new target identity by default; PA adds no tombstone/retired-target history database.
- Treats outside-current-plan holdings as current source evidence only: they disappear automatically after accepted source data no longer reports them, with no manual PA deletion step.
- Supports a bounded generic target architecture of up to 32 targets and adds a first-class structural presentation model for current targets/current-plan/outside-scope holdings.
- Migrates the repository reference plan to schema 2 using opaque target IDs; this is an explicit one-time target-entity identity migration for the reference plan, and the supplied dashboard is aligned to those IDs.
- Renames the policy dashboard label to **Exception review** / **Ausnahmeprüfung** to distinguish exception lifecycle from plan review scheduling.
- Keeps payload schema 8, REST portfolio schema 1, Gateway health schema 6, provider runtimes, freshness/schedule semantics, and the no-trading boundary unchanged.

## 1.33.1

- Fixes recurring execution/review dates so they are anchored to the latest valid Portfolio Architect evaluation instead of the oldest contributing source timestamp.
- Reproduces the live 18-August topology: monthly day 7 now yields 7 September scheduled execution and 5 October next review even with a valid 31-July DKB CSV.
- Preserves v1.33.0 evidence-kind freshness, schedule/file-plan persistence separation, provider runtimes, wire schemas and the advisory/no-trading boundary.

## 1.33.0

- Separates provider-evidence freshness from recurring plan review scheduling: future review dates can no longer make old bank evidence fresh, and overdue reviews no longer rewrite source freshness.
- Adds explicit bounded evidence-kind freshness thresholds for live API/Gateway, imported statement, imported CSV and other evidence, with conservative migration from the existing global threshold.
- Keeps an existing stale plan stale on upgrade until the operator deliberately saves different provider/evidence-kind limits.
- Fixes `Restore file-based plan` so it removes only the Home Assistant target-plan override and preserves recurring execution/review schedule options.
- Adds an independent `Execution & review schedule` configuration flow so schedule timing can be restored or changed while targets continue to come from `portfolio.yaml`.
- Reuses the v1.32 per-source freshness/dashboard evidence with each source's effective threshold; provider runtimes, wire schemas, diagnostic policy and the advisory/no-trading boundary remain unchanged.

## 1.32.0

- Adds per-source freshness evidence so stale multi-source actionability can identify the exact blocking source, evidence kind, age and unchanged aggregate freshness threshold.
- Adds bounded English/German freshness and actionability summaries to native Home Assistant entities and reference dashboards while preserving the existing oldest-source fail-closed rule.
- Introduces a provider-diagnostics evidence policy covering App-private persistence, allowlisted/sanitized operator text, Ingress safety, raw-response/document exclusion and secret-leak regression requirements.
- Persists only the latest bounded Trade Republic statement-import outcome with allowlisted diagnostic text in mode-`0600` App-private state; the private PDF remains memory-only and is deliberately not fingerprinted.
- Audits Comdirect diagnostics/Ingress behavior against the same policy without changing its authenticated acquisition, OAuth/session or wire contracts; DKB v1.31.2 probe diagnostics remain unchanged.
- Keeps payload schema 8, REST portfolio schema 1, Gateway health schema 6, portfolio actionability semantics, provider acquisition and the advisory/no-trading boundary unchanged.

## 1.31.2

- Hardens the DKB anonymous FinTS BPD probe after the first live registered attempt reached the fixed endpoint but exposed Ingress-navigation and diagnostic-state defects.
- Requires the issued FinTS registration ID to be exactly 25 alphanumeric characters and proves the complete value occurs exactly once in `HKVVB`'s product-designation field.
- Makes DKB Ingress POST redirects relative to the App root so Store/Probe actions cannot navigate the iframe to Home Assistant's absolute `/`.
- Persists bounded probe outcomes so failed attempts no longer disappear back to `ready / not probed`; valid FinTS return-code responses without BPD are retained as `bank_rejected` together with bounded sanitized `HIRMG`/`HIRMS` operator text.
- Keeps DKB experimental/manual-only/non-live, discards raw responses after extracting bounded diagnostics and a response fingerprint/length, and adds no login, PIN/TAN, holdings, order, transfer, payment or transaction-history operation.
- Records future user-configurable target architecture and first-class dynamic portfolio presentation as roadmap goals rather than hard-coding more current-plan entities into the dashboard.
## 1.31.1

- Fixes live v1.31.0 acceptance where a Trade Republic ISIN-only holding became outside current plan scope and the Home Assistant payload parser rejected its intentionally empty WKN.
- Restores the established ISIN-first identity contract: whole-portfolio holdings may omit WKN when a non-empty ISIN is present, while holdings with neither identity still fail closed.
- Excludes empty WKN placeholders from duplicate-WKN detection so multiple legitimate ISIN-only holdings remain valid without inventing provider metadata.
- Adds an end-to-end regression for the exact live topology: accumulating Robotics is the active target, the distributing Robotics holding comes only from Trade Republic with no WKN, remains outside scope, and the complete Home Assistant model parses successfully at six-of-seven target coverage.
- Keeps the v1.31 canonical target, superseded exception, schema-2 execution-provider configuration, payload schema 8, REST schema 1, Gateway health schema 6, provider acquisition, private-PKI HTTPS, and advisory/no-trading boundary unchanged.

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
