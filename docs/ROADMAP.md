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

Current milestone: allow one Portfolio Architect instance to consume several
independent provider Gateway REST snapshots simultaneously without teaching the
portfolio engine any provider-specific acquisition format.

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

## Later provider acquisition work

The DKB App still requires its own supported acquisition/import design before it can
replace or complement the existing DKB CSV source. Provider-specific acquisition
must remain inside the corresponding Gateway App; Portfolio Architect should
continue to consume only canonical provider-neutral snapshots.
