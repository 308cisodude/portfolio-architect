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
