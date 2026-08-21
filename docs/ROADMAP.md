# Portfolio Architect roadmap

This roadmap records intended sequencing rather than a compatibility promise. Each
milestone remains subject to design, security review, tests, and live acceptance.

## v1.22.0 — publication and privacy hardening

Completed: source/history/artifact privacy gates and immutable secret scanning are
release invariants.

## v1.23.0 — provider-aware Gateway foundation

Completed: the hardened Gateway server consumes a provider-neutral runtime contract
and health schema 6 carries bounded provider identity. The existing Comdirect App
retained its historical slug/private state.

## v1.24.0 / v1.24.1 — distinct provider Gateway Apps

Completed: three separately installable provider App identities with isolated
private storage: **Portfolio Architect Gateway — Comdirect**, **Portfolio Architect
Gateway — DKB**, and **Portfolio Architect Gateway — Trade Republic**. Version
v1.24.1 corrected reduced-shell startup and added protected running-container smoke
tests.

Comdirect remains the stable live provider. DKB remains an experimental fail-closed
shell until a separate supported acquisition design is implemented.

## v1.25.0 — Trade Republic statement import

Completed and live-accepted: the separate Trade Republic App accepts the supported
German text-PDF `DEPOTAUSZUG` holdings-statement family through its admin-only
Ingress page, parses the document locally in memory, and publishes only a validated
provider-neutral holdings snapshot through REST schema 1.

real Trade Republic statements remain private input; public tests use wholly synthetic documents/fixtures only, generated as runtime PDF data; unsupported/ambiguous documents fail closed.

## v1.26.0 — multiple Gateway REST aggregation

Published, but not accepted as the known-good multi-provider baseline: the release
successfully added/validated the Trade Republic Gateway and exposed three portfolio
sources in live operation, while live acceptance revealed that the calculation path
still assumed target holdings were keyed by WKN. An ISIN-only Trade Republic
Robotics holding therefore remained outside the configured target architecture.

The milestone requires:

- preserving the existing primary REST configuration and adding/removing additional
  local Gateways through config-entry options;
- health-schema-6 provider identity and live snapshot validation before an
  additional Gateway is accepted;
- atomic aggregation with no silent provider dropout;
- source-set-aware Home Assistant LKG retention during an additional-Gateway outage;
- distinct `provider_count` / `provider_ids` metadata alongside source-instance
  count and existing per-position provenance;
- the reference dashboard showing a distinct-provider summary; and
- Trade Republic auto-start once it can be a persistent REST contributor.

Payload schema 8, REST schema 1, Gateway health schema 6, entity IDs, authorized-cash
semantics and the read-only/no-trading boundary remain unchanged.

## v1.26.1 — ISIN-first identity hotfix

Completed and live-accepted: ISIN is the canonical instrument identity, WKN is an
unambiguous fallback only when ISIN is unavailable, and contradictory identity
evidence fails closed. Live acceptance established the first known-good
three-source/three-provider 7/7 aggregate and proved atomic Trade Republic
outage/LKG/recovery behavior without silent provider dropout.

## v1.26.2 — dashboard and outage UX polish

Published and functionally accepted except for one remaining German Tile-card
presentation edge case: Home Assistant substitutes its own frontend-language
`Unavailable` label once an entity itself becomes unavailable, even if the entity
still exposes an explicit German presentation attribute.

- Make the German reference dashboard render explicit German state values
  independently of the global Home Assistant frontend language.
- Preserve stable machine-readable entity states for automations/API consumers.
- Identify the privacy-safe configured source instance or instances that currently
  prevent a live aggregate.
- Collect multiple supplemental Gateway failures for presentation while preserving
  atomic all-configured-source aggregation/LKG semantics.
- Replace the supplemental-outage `Attention reason: None` presentation with the
  existing bounded `supplemental_source_unavailable` reason and translations.
- Keep payload schema 8, REST schema 1 and Gateway health schema 6 unchanged.

## v1.26.3 — dashboard presentation and policy-layout follow-up

Published and live-accepted for the German unavailable-state workaround, compact
policy layout, source-specific outage diagnostics, and atomic LKG recovery. Live
acceptance exposed one remaining cosmetic inconsistency: date-only Tile states still
rendered as raw ISO `YYYY-MM-DD` values.

## v1.26.4 — native date-tile formatting attempt

Published. Live acceptance proved that Home Assistant's Tile `time_format` does not
locale-format a `sensor` state merely because that sensor uses
`SensorDeviceClass.DATE`; the affected Tiles continued to show raw `YYYY-MM-DD`.
The underlying DATE sensor contract remained correct and unchanged.

## v1.26.5 — native date-domain presentation

Published and live-accepted. The five authoritative DATE sensors remain unchanged,
while additive read-only native `date.*` counterparts now give Home Assistant the
correct semantic domain for locale-aware date presentation. Live acceptance also
exposed one unrelated source-diagnostics edge case: during Comdirect
reauthentication, a reachable Gateway serving its own trusted cached snapshot could
leave **Source unavailable** without a bounded source ID.

## v1.26.6 — non-live REST Gateway source diagnostics

Published and live-accepted. Reachable non-live REST Gateways are now identified through bounded source metadata even while the Gateway itself serves trusted cached data. The overnight acceptance test that proved this fix also exposed a separate cold-restart snapshot-identity defect in the common Gateway runtime.

## v1.26.7 — cold-restart snapshot identity hotfix

Completed and live-accepted. Persisted quantity-bearing Gateway snapshots now retain
byte-identical content/fingerprint across restart, and `If-None-Match` correctly
takes precedence over `If-Modified-Since`. The v1.26 multi-provider/resilience line
is complete.

## v1.27.0 — Gateway HTTPS transport hardening

Current milestone: replace plaintext HTTP on the private Home Assistant App network
with certificate-verified HTTPS without weakening the existing bearer-authenticated,
local-only, DNS-pinned Gateway boundary.

- Give each official provider App a persistent per-installation private CA and
  hostname-valid server certificate.
- Keep CA/server private keys inside App-private `/data/gateway/tls` state.
- Publish only public CA trust plus bounded provider/endpoint identity through
  Home Assistant Supervisor discovery.
- Update Portfolio Architect first, then migrate each configured Gateway only after
  the discovered HTTPS health endpoint validates with its existing bearer token.
- Refuse silent CA replacement and never downgrade an already migrated source to
  plaintext HTTP.
- Require explicit user confirmation before a newly discovered supplemental provider
  is added to an existing portfolio.
- Preserve local-address validation, DNS pinning, Host/SNI/certificate identity,
  payload schema 8, REST schema 1, health schema 6, provider isolation, atomic LKG
  behavior and the read-only/no-trading boundary.

mTLS remains a separate future design question; v1.27.0 deliberately retains the
dedicated bearer token as the application-layer authentication factor.

## Later provider acquisition work

The DKB App still requires its own supported acquisition/import design before it can
replace or complement the existing DKB CSV source. Provider-specific acquisition
must remain inside the corresponding Gateway App; Portfolio Architect should
continue to consume only canonical provider-neutral snapshots.

## v1.27.1 — immutable-publication workflow parity hotfix

Current publication milestone: publish the completed v1.27 HTTPS transport hardening
without changing production integration or Gateway runtime behavior.

- Keep the v1.27.0 private-PKI HTTPS, Supervisor discovery, bearer authentication,
  hostname verification, trust migration and fail-closed behavior unchanged.
- Make the tag-triggered immutable-release provider-shell smoke test use the same
  bounded mock Supervisor and ephemeral Supervisor token as protected PR validation.
- Exercise an actual hostname-checked TLS handshake against the generated private CA
  in both workflow paths.
- Require the provider-shell smoke-test bodies in `validate.yml` and `release.yml` to
  remain identical so future transport prerequisites cannot drift between merge and
  publication gates.
- Preserve payload schema 8, REST schema 1, health schema 6, provider acquisition,
  portfolio calculations, entity contracts, LKG semantics and the read-only/no-trading
  boundary.


## v1.27.2 — Supervisor discovery migration eligibility hotfix

Current hotfix: allow Home Assistant Supervisor discovery flows to reach Portfolio
Architect even when the one intended config entry already exists, so a legacy HTTP
Gateway source can be migrated to verified HTTPS. The manifest-level
`single_config_entry` shortcut is removed because Home Assistant suppresses *all* new
config flows when an entry exists, including the trusted `hassio` discovery flow.
Portfolio Architect keeps the one-entry invariant explicitly in `async_step_user`,
with the stable unique ID retained as defense in depth. Existing verified-HTTPS
trust validation, bearer authentication, provider identity checks, no-plaintext
fallback, schemas, portfolio calculations and LKG behavior remain unchanged.


## v1.27.3 — DKB discovery identity hotfix

Current narrow follow-up: live v1.27.2 acceptance proved Comdirect and Trade Republic
verified-HTTPS migration, but exposed one pending DKB discovery card because the DKB
Gateway provider ID `dkb` was compared with the DKB CSV source ID `dkb_csv`. Keep
Gateway and importer provider namespaces explicit, suppress duplicate DKB scope across
all setup paths, and preserve the live-proven v1.27.2 TLS/migration architecture
unchanged.

## v1.27.4 — Comdirect OAuth cadence hotfix

Current narrow follow-up: live testing proved a timing-dependent Comdirect OAuth
renewal race when PhotoTAN bootstrap occurs shortly before a fixed 15-minute
portfolio refresh. A still-usable access token can let that refresh skip OAuth
renewal, leaving the refresh session to age past its short provider window before
the following portfolio cycle. Keep provider-specific authentication lifecycle
inside the Comdirect Gateway, add an independent maintenance cadence with no
portfolio acquisition, and preserve all v1.27 HTTPS/wire/provider-neutral
contracts unchanged.

## v1.28.0 — DKB FinTS registration and capability-probe milestone

Current provider-research milestone: begin the DKB acquisition path without assuming
that DKB exposes depot holdings through FinTS for this user relationship and without
introducing authenticated bank credentials before Portfolio Architect has its own
legitimate FinTS product identity.

- Require Portfolio Architect's own FinTS product registration number before any DKB
  probe can run; do not reuse a library/kernel registration in production.
- Keep the DKB App experimental and `manual_only` with provider identity `dkb`.
- Add only an anonymous FinTS 3.0 BPD dialog initialization against DKB's fixed
  documented endpoint `https://fints.dkb.de/fints` and bank code `12030000`.
- Send no holdings, balance, transaction, order, transfer, payment or debit business
  transaction in this milestone.
- Reduce the raw BPD response to bounded capability metadata and discard the raw bank
  response immediately.
- Treat `HIWPDS` advertisement only as bank-level evidence to continue research, not
  as authority to fetch holdings.
- Keep DKB login/PIN/TAN and DKB-App decoupled authentication out of v1.28.0.
- Before any later holdings implementation, require an authenticated user-capability
  / UPD gate proving that the user relationship advertises a suitable read-only
  securities capability.
- If that authenticated capability is absent, keep the Gateway fail-closed and
  consider a local DKB securities-document import rather than private web/mobile
  interface scraping.
- Preserve the established provider namespace distinction: Gateway identity `dkb`
  remains separate from CSV importer identity `dkb_csv`, with collision suppression
  preventing silent double counting.
- Preserve payload schema 8, REST schema 1, health schema 6, v1.27 verified HTTPS,
  Comdirect v1.27.4 session maintenance, Trade Republic statement import and the
  no-trading/write-capability boundary.


## v1.28.1 — GitHub Actions Node.js 24 runtime maintenance

- Keep every GitHub Action reference immutable and full-SHA pinned.
- Refresh all four `actions/checkout` workflow invocations to official v7.0.1.
- Refresh `actions/setup-python` in validation and immutable publication to official v7.0.0.
- Reject mutable action tags and the temporary insecure Node.js runtime opt-out in regression coverage.
- Preserve the v1.28.0 DKB FinTS registration/capability-probe gate and all production runtime behavior unchanged.

## v1.28.2 — Dependabot GitHub Actions grouping maintenance

- Keep the existing weekly `github-actions` Dependabot schedule and five-open-PR cap.
- Group all GitHub Actions **version updates** into one pull request per Dependabot update cycle so related action refreshes are reviewed and validated atomically.
- Keep security updates outside that version-update group; this milestone does not configure a security-update batch.
- Preserve immutable full-SHA action pinning and the v1.28.1 Node.js 24-capable action versions until a reviewed dependency update changes them.
- Preserve the v1.28.0 DKB FinTS registration/capability-probe gate and all production runtime behavior unchanged.

## v1.29.0 — policy-dashboard visual hierarchy

- Keep the accepted-exception count, concrete exception and decision/review lifecycle
  tiles unchanged.
- Insert a native conditional subtitle between the exception lifecycle and optimisation
  opportunity tiles so governance exceptions and non-critical improvements no longer
  share the same visual hierarchy.
- Surface the existing optimisation-opportunity count only as a compact native heading
  badge; keep it out of the primary tile grid and hide the subtitle entirely at zero.
- Preserve the four concrete blue opportunity tiles, their more-info interactions, all
  entity IDs/machine states, policy calculations and fail-closed availability semantics.
- Use only native Home Assistant cards; add no custom card, CSS/card-mod or Markdown
  dependency.
- Preserve provider acquisition, private-PKI HTTPS, schemas, Comdirect session
  maintenance, Trade Republic import and the v1.28 DKB FinTS gate unchanged.

## v1.30.0 — provider-aware execution policy

- Separate portfolio acquisition provenance from future purchase execution-provider
  choice.
- Preserve `broker.yaml` schema 1 and add opt-in schema 2 for multiple execution
  providers with explicit fee evidence, provenance and bounded freshness.
- Evaluate savings-plan and optional manual-order routes across fresh providers and
  expose the selected provider with each recommendation.
- Make savings-plan fee policy provider-aware so a compliant alternative route can
  remove an otherwise unnecessary fee opportunity.
- Allow accepted exceptions to bind to the preferred execution provider that justified
  the decision; reopen the exception as `review_required` when that assumption changes
  while preserving audit history.
- Detect execution-provider changes in the private decision trace and present provider
  names using native Home Assistant Tile state content.
- Keep provider Gateway acquisition, credentials, REST/health schemas, private-PKI
  transport, LKG and the advisory/no-trading boundary unchanged.

## v1.31.0 — canonical accumulating Robotics target

- Correct the active Robotics target from distributing `IE00BYWZ0333` / `A2ANH1` to
  accumulating `IE00BYZK4552` / `A2ANH0`.
- Retain the already-owned distributing instrument as an identifiable outside-current-
  plan holding: visible and valued, but never a future purchase target or automatic
  sell instruction.
- Retain the old distributing-share-class exception as validated `superseded` audit
  history instead of deleting the governance decision.
- Activate the v1.30 schema-2 execution-provider model in the current reference plan
  with exact, independently evidenced route configuration only; do not infer broad
  provider tradability from a holdings source.
- Make six-of-seven target coverage the intentional pre-purchase state until the
  accumulating Robotics share class is actually held.
- Preserve payload schema 8, REST schema 1, health schema 6, provider acquisition,
  private-PKI transport, LKG, DKB FinTS gates and the advisory/no-trading boundary.

## v1.31.1 — ISIN-only outside-scope holding hotfix

- Preserve the v1.31 canonical accumulating Robotics target and migrated plan unchanged.
- Restore the v1.26.1 ISIN-first identity contract at the Home Assistant payload boundary: an
  imported whole-portfolio holding may omit WKN when it has a valid non-empty ISIN.
- Exclude empty WKN placeholders from duplicate-WKN detection while retaining duplicate
  checks for real WKNs and ISINs.
- Fail closed when a holding exposes neither ISIN nor WKN.
- Reproduce the exact live v1.31.0 failure with a Trade Republic-only distributing Robotics
  holding that becomes outside current plan scope, and require the complete Home Assistant
  model to parse the resulting six-of-seven portfolio successfully.
- Keep provider acquisition, Gateway wire schemas, verified HTTPS, LKG, DKB FinTS gates and
  the advisory/no-trading boundary unchanged.

## v1.31.2 — DKB first-probe diagnostics hardening

- Require the issued FinTS registration identity to be exactly 25 alphanumeric characters
  and place the complete value only in `HKVVB`'s product-designation field.
- Keep registration/probe POST navigation inside the DKB Home Assistant Ingress namespace.
- Persist sanitized probe outcome state so a failed attempt cannot disappear back to
  `ready / not probed` when the Web UI is reopened.
- Preserve bounded `HIRMG`/`HIRMS` return codes and sanitized operator-message text from
  syntactically valid FinTS responses without BPD and classify them as inconclusive
  `bank_rejected` evidence.
- Redact the configured product identity if echoed, retain only a decoded-response SHA-256
  and byte count for correlation, discard arbitrary/unknown segment payload plus raw response
  bytes, and do not infer registration propagation without documented evidence.
- Keep DKB experimental, manual-only and non-live; authenticated user-capability/UPD and
  DKB-App decoupled authentication remain later gates before any holdings implementation.

## v1.32.0 — provider freshness and diagnostics foundation

- Preserve the established oldest-contributing-source fail-closed freshness/actionability
  rule and the configured aggregate freshness threshold unchanged.
- Expose bounded per-source evidence kind, timestamp, age, threshold status and explicit
  stale-source/actionability blocker summaries so operators can see which source is actually
  making a plan non-actionable.
- Surface the new blocker detail through native English/German Home Assistant Tile
  `state_content` only; add no custom frontend dependency.
- Define a common provider-diagnostics security policy based on classified bounded evidence,
  App-private persistence, provider-specific redaction and no generic raw-upstream retention.
- Persist only the latest allowlisted Trade Republic import outcome; never persist the private
  PDF or add a stable PDF fingerprint merely for troubleshooting.
- Audit/regression-protect Comdirect's existing bounded authenticated error model without
  adding upstream free-text or response fingerprint persistence.
- Preserve the live-accepted v1.31.2 DKB anonymous FinTS diagnostics and non-live research
  boundary unchanged apart from normal package metadata.

## v1.33.0 — source freshness and plan-schedule separation

- Evaluate provider evidence age independently from recurring review scheduling; a future review
  date cannot make stale bank evidence fresh and an overdue review cannot rewrite source
  freshness.
- Add explicit bounded user-owned evidence-kind thresholds for live API/Gateway snapshots,
  imported statements, imported CSV evidence and other sources.
- Preserve the pre-v1.33 global threshold for every evidence kind until the operator explicitly
  saves the new settings, preventing an upgrade from making an existing stale plan actionable.
- Keep one-stale-source fail-closed actionability and invalid/future timestamp rejection.
- Correct `Restore file-based plan` so it removes only the target-plan definition override and
  preserves recurring execution/review schedule options.
- Add a dedicated schedule options flow so timing can be restored/configured independently of
  whether targets come from `portfolio.yaml` or a Home Assistant override.
- Reuse the v1.32 native blocker presentation and provider diagnostic policy without adding a
  frontend dependency or changing provider runtime/wire contracts.

Any future materiality-based freshness exception (for example ignoring a small stale
contribution) still requires a separate bounded error model and must not be inferred merely
from current portfolio value.

## v1.33.1 — recurring schedule anchor hotfix

- Correct the remaining legacy schedule dependency exposed by v1.33.0 live acceptance.
- Derive scheduled execution and next plan review from the latest valid Portfolio Architect
  evaluation timestamp, never from the oldest contributing source timestamp.
- Keep source timestamps authoritative only for their own v1.33 evidence-age freshness policy.
- Preserve the v1.33.0 configuration, provider runtime, wire-schema and fail-closed boundaries.

## v1.34.1 — whole-portfolio allocation presentation hotfix

- Ensure every configured target has a whole-portfolio allocation entity, including missing targets at 0%.
- Align reference-dashboard outside-scope distribution bindings with established ISIN-first holding IDs.
- Keep the static outside-scope detail Tile inventory and future dynamic native-dashboard milestone unchanged.

## v1.34.0 — generic target architecture and first-class presentation model

- Promote current strategic target identity to schema-2 opaque `target_id` values generated from 128 random bits; retain schema-1 `id` and payload `fund_id` only for compatibility.
- Keep target identity independent from ISIN, WKN, display name, target order and weight; ISIN remains canonical instrument identity and WKN remains secondary fallback/validation metadata.
- Generate a fresh target ID in the native plan editor only when a genuinely new current target role is created; never derive it from an instrument.
- Keep PA current-state-only: deleting a target does not create a tombstone/retired-target registry, and later re-adding the same ISIN creates a fresh target identity.
- Treat outside-current-plan holdings as accepted source evidence only; they disappear automatically when no accepted source reports them and are never stored in an outside-scope history registry.
- Keep the bounded arbitrary target count at maximum 32 and exact 100% positive-weight validation; the seven-ETF retirement architecture becomes reference configuration only.
- Add a bounded first-class `presentation_model` sensor containing current configured targets, current-plan holding identities, complete current outside-scope inventory, source provenance and aggregate policy/actionability state.
- Keep high-churn monetary/action guidance on dedicated entities rather than duplicating it into the structural presentation index.
- Rename the ambiguous policy-dashboard `Next review` label to `Exception review` while keeping plan-review and exception-review clocks distinct.
- Add no custom frontend dependency; the reference dashboard remains static until the following dynamic-presentation milestone.

## v1.35.0 — provider-scoped cash and funding topology

- Preserve authorized investment cash as provider-owned evidence across all accepted REST Gateway
  snapshots instead of collapsing supplemental-provider cash into one global reserve.
- Add broker schema 3 with explicit directed funding-transfer relationships, operator-owned
  transfer fees and conservative settlement time in business days; never infer the reverse edge.
- Evaluate funding provider and execution provider together. Include transfer cost in route
  economics and use settlement delay only after economic cost when otherwise choosing between
  equivalent routes.
- Keep same-provider funding implicit and free; cross-provider funding is unavailable unless the
  exact directed relationship is configured. Multiple provider cash pools remain separate and are
  debited only by recommendations that actually use them.
- Expose bounded advisory transfer plans plus provider cash remaining after recommendations while
  preserving established `all_available`/`capped` authorization semantics.
- Keep Portfolio Architect strictly advisory: no money movement, order placement, transaction
  history, inferred execution, or sell capability is introduced.
- Preserve REST portfolio schema 1, Gateway health schema 6, private-PKI HTTPS, bearer
  authentication, Supervisor trust discovery, DNS pinning and provider isolation.
- Quietly disambiguate the accumulating Robotics reference-dashboard label from the retained
  distributing outside-scope holding and add raw DKB capability-probe response-body SHA-256/byte
  evidence without persisting the response body itself.

## v1.35.1 — Comdirect session-maintenance resilience hotfix

- Classify direct connection-reset/connection errors from the Comdirect HTTPS stack as bounded
  retryable remote-API failures rather than allowing a socket exception to escape the provider
  transport boundary.
- Contain unexpected ordinary exceptions per maintenance iteration so the provider-specific
  five-minute OAuth worker cannot be terminated by one transient/unclassified failure.
- Keep exception diagnostics privacy-bounded to the exception type and preserve conclusive OAuth
  rejection/PhotoTAN behavior unchanged.
- Correct the two remaining German accumulating-Robotics allocation-chart labels.
- Preserve v1.35.0 funding topology, wire schemas, verified HTTPS, provider isolation and the
  advisory/no-trading boundary.

## v1.35.2 — execution-policy UX and retained cash

- Add a native Home Assistant editor over validated file-backed broker schemas 2 and 3 for provider evidence, savings-plan routes and exact directed funding topology.
- Present numeric provider priority as an optional tie-break preference; keep cost first and settlement time second.
- Validate `promotional` as boolean descriptive tariff/provenance metadata and keep it outside route economics.
- Add provider-owned **Keep cash reserve** authorization with `authorized = max(eligible - retain, 0)` while preserving all-available/capped compatibility.
- Keep DKB non-live and do not generalize funding topology into arbitrary transit-bank graph nodes.
- Preserve payload schema 8, REST portfolio schema 1, Gateway health schema 6, private-PKI transport and advisory-only behavior.

## v1.35.3 — execution-policy menu-label hotfix

- Restore the missing Home Assistant list-menu translations for all native execution-provider, savings-plan and funding-topology menus introduced in v1.35.2.
- Cover every emitted broker-editor menu option in both English and German so unlabeled chevrons cannot regress.
- Preserve broker schemas, route economics, retained-cash authorization, provider behavior, wire schemas and the advisory/no-trading boundary unchanged.

## v1.35.4 — locale-tolerant cash-policy input hotfix

- Accept common human EUR amount formats for Comdirect cash caps and retained reserves, including German decimal comma and validated dot/comma/space/apostrophe grouping, while keeping private state canonical.
- Replace the live-observed generic invalid-amount HTTP 400 with bounded non-sensitive Ingress guidance and preserve the previous valid policy on rejected input.
- Preserve cash-policy mathematics, provider-scoped funding, broker semantics, Gateway schemas/transport and all no-trading boundaries.
- Preserve broker schemas, route economics, retained-cash authorization, provider behavior, wire schemas and the advisory/no-trading boundary unchanged.

## v1.36.0 — native dynamic portfolio presentation

- Consume the v1.34 structural presentation contract through bounded diagnostic presentation-slot adapters so the reference dashboard renders the actual configured target, outside-scope and active-policy inventory without instrument-specific YAML lists.
- Use only native Home Assistant `entity-filter`, Entities, Glance, Distribution, Tile and Conditional cards; add no `auto-entities`, card-mod, custom JavaScript or custom-card dependency.
- Keep opaque `target_id` and accepted holding `position_id` as stable portfolio identity; presentation slots are explicitly ephemeral UI projections and repeat the stable identity in attributes.
- Match dashboard candidate ranges to the accepted backend bounds (32 targets, 512 holdings, 256 policy findings) and expose presentation schema 2 slot metadata for exact reconciliation.
- Keep user-owned dashboard copies opt-in: HACS/integration updates never overwrite an imported or personalized Lovelace dashboard.
- Preserve all v1.35 execution-policy, funding, retained-cash and Gateway security/runtime contracts.

## v1.36.1 — dynamic native-dashboard hotfix

- Replace only the live-broken `entity-filter` → Distribution composition with native filtered Entities lists; retain the v1.36.0 presentation schema 2 backend and slot bounds unchanged.
- Request entity-only Home Assistant display names for dynamic candidates so the `Portfolio Architect` device prefix does not crowd instrument labels.
- Preserve all provider, execution/funding, retained-cash, wire-schema, private-PKI and advisory/no-trading contracts.

## v1.37.0 — shared human-input validation foundation

- Centralize reusable syntax normalization and bounded type validation for opt-in human numeric fields: EUR/money, percentages, quantities and bounded integers.
- Keep field/provider semantics separate: shared mechanics produce a canonical typed value, then provider-specific validation decides whether it is meaningful.
- Reject ambiguous cross-locale quantity syntax rather than guessing; accept locale-style grouping/decimal syntax only when the primitive can interpret it safely.
- Invalid human input returns bounded guidance, preserves previous valid state and never reflects rejected raw input or arbitrary exception text.
- Migrate only the existing Comdirect capped/retained cash amount fields onto the shared EUR primitive, preserving the live-proven v1.35.4 accepted syntax and canonical private persistence.
- Mirror the helper consistently into all provider App build contexts for future opt-in use, while leaving unused provider paths behaviorally unchanged.
- Protocol identifiers, registrations, credentials, tokens and exact IDs bypass human-numeric normalization; DKB FinTS registration and Trade Republic statement import retain their provider-specific validation paths.
- Preserve REST schema 1, health schema 6, presentation schema 2, broker schemas 1/2/3, private-PKI transport, provider behavior and the advisory/no-trading boundary.

## v1.38.0 — native dashboard stardust

- Restore copy-friendly recommendation interaction without hard-coded instrument inventory: tapping a visible dynamic recommended-purchase amount opens the same slot's ISIN entity, while holding the row opens the existing purchase explanation.
- Add bounded policy-aware context to the native **Authorized investment cash** Tile: total available cash and the amount excluded by the active all-available/capped/retained policy.
- Add the same total/policy context plus planned cash outlay to **Cash after recommended purchases**, so the visible figures reconcile as `remaining + policy excluded + planned = total available` when all evidence is present.
- Derive the context only from already validated provider-neutral cash evidence; if provider-scoped eligibility/authorization evidence is incomplete, omit the context rather than guessing.
- Keep the v1.36 presentation-slot backend, bounded candidate ranges and native-only dashboard architecture unchanged; add no custom frontend dependency or hard-coded target/holding identity.
- Preserve v1.37 shared human-input validation, provider runtimes, Gateway wire/security contracts, funding/cash mathematics and the advisory/no-trading boundary.

## v1.38.1 — native dynamic drift stardust

- Restore signed per-target allocation-drift visualization for all 32 bounded generic target presentation slots without reintroducing instrument-specific YAML.
- Select amber, green or red native Tile presentation through core Conditional cards based on the slot's `underweight`, `on_target` or `overweight` status.
- Use the Tile-native `bar-gauge` on a stable -100…+100 percentage-point range and retain the entity's dynamic instrument name.
- Make each visible drift Tile open the matching bounded allocation explanation on tap; no frontend calculation or separate synthetic target marker is added.
- Preserve the v1.38.0 copy-friendly recommendation ISIN interaction and policy-aware cash context, presentation schema 2, provider runtimes, Gateway wire/security contracts and advisory/no-trading boundary.

## v1.39.0 — dynamic colourful allocation presentation

- Replace the current/target allocation entity-filter lists with paired native Conditional + Tile cards across the same 32 bounded generic target presentation slots.
- Use a deterministic native colour palette per presentation slot so current and target views share position identity without persisting colour into portfolio semantics.
- Use native 0–100% bar gauges and condition current visibility on target membership so configured-but-missing targets remain visible at 0% current allocation.
- Preserve v1.38.1 signed drift status colours, gauges and explanation tap-through unchanged.
- Preserve presentation schema 2, provider runtimes, wire/security contracts, cash/funding mathematics and the advisory/no-trading boundary.

## v1.40.0 — evidence-backed funding transfers

- Keep broker schema 3 and its exact directed funding topology; add optional bounded `source` + `as_of` provenance to each transfer edge without inventing transfer capability from provider identity.
- Make the native broker editor create evidence-backed edges and require verified fee, conservative business-day availability, evidence source and evidence date together.
- Reuse the existing `fee_data_max_age_days` evidence window for evidenced funding edges; stale edges stay parseable but fail closed for route selection until refreshed.
- Preserve legacy provenance-free schema-3 edges for backward compatibility, while future/partial evidence fails closed and reverse transferability is never inferred.
- Keep provider-scoped cash pools separate and Portfolio Architect advisory-only: no transfer initiation, payment API, order placement, transaction history or inferred execution is added.
- Preserve v1.39.0 dashboard presentation, provider acquisition, REST schema 1, health schema 6, presentation schema 2 and verified private-PKI transport.

## v1.40.1 — Configure-form compatibility hardening

- Fix the Home Assistant 2026.8.1 NumberSelector floor violation that prevents savings-plan route forms from opening.
- Audit every native Configure selector/mode/step and all options-flow destinations/translations.
- Use native DateSelector controls for broker evidence dates with Home Assistant-local current-date defaults for new evidence.
- Surface bounded duplicate provider/route/funding-edge errors without weakening generic fail-closed validation.
- Preserve v1.40.0 evidence-backed funding semantics, broker schemas, provider runtimes and dashboard presentation.

## v1.41.0 — Trade Republic cash-statement acquisition

- Add a separate strict German text-PDF `KONTOAUSZUG` parser inside the Trade Republic App while retaining `DEPOTAUSZUG` holdings as an independent evidence family.
- Persist only bounded normalized provider-scoped cash state; do not retain PDFs, transaction rows, counterparties, IBAN/account identifiers, names or addresses.
- Reconcile `Cashkonto` arithmetic and trust-account/QMMF custody totals before accepting cash.
- Keep holdings and cash evidence timestamps independent through REST schema 1 and freshness-gate provider cash separately using the existing `imported_statement` threshold.
- Preserve the advisory-only execution boundary and avoid undocumented/private Trade Republic APIs entirely.

## v1.41.1 — Local-cash funding tie-break hotfix

- Prefer execution-provider-local cash when it is otherwise economically identical to a transfer-funded candidate.
- Preserve cost-first routing, settlement-time ordering, explicit provider priority, order amount and fee semantics before applying the local-cash preference.
- Add executable zero-fee/zero-day parity regression coverage; no provider acquisition, schema, dashboard or money-movement capability changes.

## v1.42.0 — Normalized execution-path presentation

- Expose the already-decided actionable funding/purchase sequence as a bounded Home Assistant presentation contract rather than asking Lovelace to infer route semantics.
- Add bilingual plain/Markdown instructions for provider-local cash, advisory funding transfers, mixed funding and purchases, with conservative settlement-day wording and an explicit advisory-only footer.
- Render the integration-owned localized Markdown through one native Home Assistant card per dashboard locale; no custom card, JavaScript or routing logic enters the frontend.
- Preserve v1.41.1 funding economics, provider acquisition, schemas, verified HTTPS and the no-money-movement boundary.

## Deferred beyond v1.42.0

- **DKB authenticated acquisition:** remains gated on legitimate product registration/capability evidence and later authenticated user-capability/UPD validation; do not infer holdings support from generic or anonymous bank capability lists.
- The historical accepted-exception horizontal-overflow wart is no longer an outstanding item: the v1.36 native dynamic policy list replaced that old static presentation path.

v1.41.1 retains bounded local Trade Republic cash-statement acquisition and changes only the funded-route tie-break; no new remote provider API or transaction capability is enabled. v1.42.0 adds only presentation of those already-decided instructions and likewise enables no new remote provider API or transaction capability.
