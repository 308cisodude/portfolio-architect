# Portfolio Architect 1.31.0

Version 1.31.0 is a narrow current-plan and policy-governance correction prepared from
the exact published and live-accepted v1.30.0 baseline. It fixes the abstraction exposed
during v1.30 live acceptance: the instrument that was historically allowed by an
exception must not remain the canonical target after the preferred accumulating share
class becomes a valid execution route. Portfolio Architect remains advisory and
read-only.

## Canonical Robotics target

The active Robotics allocation now targets:

- ISIN `IE00BYZK4552`;
- WKN `A2ANH0`;
- accumulating share class; and
- the existing 5% target weight.

The former distributing target `IE00BYWZ0333` / `A2ANH1` is no longer part of the
active allocation. Its instrument metadata remains available so an already-owned
distributing position can still be identified and valued.

An existing distributing holding therefore becomes an ordinary **outside current plan
scope** holding. It continues to contribute to total portfolio value and whole-portfolio
allocation views, but it does not satisfy the active Robotics target, receives no future
purchase recommendation, and never creates an automatic sell instruction. Before the
first accumulating holding is acquired, an otherwise complete seven-target portfolio is
expected to report six of seven active targets held.

## Historical exception lifecycle

Exceptions schema 2 now accepts an explicit terminal audit state, `superseded`. A
superseded entry is strictly validated but is not an active policy exception. It does
not contribute to either the accepted-exception count or the review-required count.

The historical `robotics_distributing_share_class` decision is retained with its
original approval date and Comdirect route assumption, plus bounded supersession
metadata:

- `superseded_on`;
- `superseded_by_instrument_id`; and
- `superseded_reason`.

The history is therefore preserved without pretending that an exception is still needed
for current planning. Unknown exception states, future supersession dates, malformed
replacement instruments, and invalid audit metadata fail closed.

## Exact provider-aware execution evidence

The current reference `broker.yaml` now uses the v1.30 schema-2 provider model. Existing
Comdirect evidence remains present, and the accumulating Robotics ISIN gains one explicit
Trade Republic savings-plan route with its own provenance and evidence date.

This is intentionally **instrument-specific**. The configuration does not infer that
other target instruments are eligible at Trade Republic, does not infer provider-wide
manual-order availability, and does not derive execution eligibility from a Trade
Republic portfolio source. Fee evidence remains bounded by the v1.30 freshness contract.

## Dashboard and scope presentation

The reference allocation views now show both concepts separately:

- the canonical accumulating Robotics target in the whole-portfolio distribution; and
- the former distributing Robotics holding as a compact outside-plan holding when it is
  present.

The English outside-plan label is `Robotics · Dist`; the German reference uses
`Robotik · Aussch.`. No custom frontend code, CSS, card-mod, or Markdown card is added.

## Preserved boundaries

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported
- v1.30 provider-aware execution engine: retained
- portfolio-source identity and execution-provider identity remain separate
- provider Gateway acquisition and credentials: unchanged
- v1.27 private-PKI verified HTTPS, bearer authentication, Supervisor trust discovery,
  DNS pinning and no-plaintext fallback: unchanged
- Comdirect v1.27.4 OAuth/session maintenance: unchanged
- Trade Republic statement import/private snapshot behavior: unchanged
- this release does not move PDF parsing into Portfolio Architect
- v1.28 DKB FinTS registration/capability-probe gate: unchanged
- v1.28.1 immutable GitHub Actions pins and v1.28.2 Dependabot grouping: unchanged
- v1.29 native policy-dashboard hierarchy: retained
- No trading, order, transfer, payment, or transaction-history capability is added
- no automatic sell capability is added

DKB remains experimental, manual-only and non-live. A FinTS product registration number
is still required before the existing anonymous BPD capability probe can run; this
release does not embed or assume an unissued registration identity. DKB live Gateway acquisition remains a later authenticated milestone. The historical `v1.19.0-rc2`
experimental brokerage probe remains excluded and is not promoted by this release.

See `docs/EXECUTION-PROVIDERS.md` and `docs/UPGRADE-1.31.0.md`.
