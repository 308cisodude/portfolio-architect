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

Current milestone: make an unchanged persisted Gateway snapshot retain exactly the same body/fingerprint across restart and correct HTTP conditional-validator precedence.

- Preserve optional position quantity through cached-snapshot reload.
- Prove save/load of quantity-bearing snapshots is byte-for-byte stable.
- Give `If-None-Match` precedence over `If-Modified-Since`; a non-matching ETag must return `200`.
- Keep fail-closed Portfolio Architect integrity checks unchanged.
- Make no OAuth/session, provider-acquisition, calculation, dashboard/date, REST-schema or health-schema change.

## v1.27.0 — Gateway HTTPS transport hardening

Next security-hardening milestone: use authenticated HTTPS for
Gateway-to-Portfolio-Architect transport on the private Home Assistant App network.
Certificate provisioning, validation, trust/pinning and renewal must survive normal
App upgrades without disabling TLS verification or replacing the existing dedicated
bearer authentication. Each Gateway must retain its own private key/trust identity;
mTLS may be evaluated separately rather than assumed.

## Later provider acquisition work

The DKB App still requires its own supported acquisition/import design before it can
replace or complement the existing DKB CSV source. Provider-specific acquisition
must remain inside the corresponding Gateway App; Portfolio Architect should
continue to consume only canonical provider-neutral snapshots.
