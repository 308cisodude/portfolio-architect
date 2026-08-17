# Portfolio Architect 1.31.2

Version 1.31.2 is a narrow DKB FinTS capability-probe hardening release prepared from the
exact immutable v1.31.1 baseline after the project's first live registered anonymous BPD
attempt exposed three provider-App issues: registration-length validation was looser than
the issued FinTS contract, Ingress POST redirects escaped to Home Assistant's root UI, and
failed probe evidence was not persisted.

## First registered-probe evidence

The v1.31.1 live attempt stored Portfolio Architect's newly issued FinTS registration
identity, reached `https://fints.dkb.de/fints` over verified HTTPS, received an HTTP-success
response, and then ended in `ProtocolError`. The raw bank response had already been
discarded by design, so the exact protocol reason could not be reconstructed. Reopening the
App then misleadingly showed `ready / not probed` because only successful probe results
were persisted.

Version 1.31.2 retains the privacy boundary while making the sanitized result durable and
useful.

## Exact 25-character HKVVB identity

The issued FinTS registration contract requires the full 25-character registration ID in
`HKVVB`'s product-designation field and nowhere else. v1.31.2 therefore:

- accepts exactly 25 alphanumeric registration characters, not 1–25;
- requires the same exact length in the App Web UI;
- places the complete registration ID exactly once in the `HKVVB` product-designation
  field; and
- keeps the separate bounded product-version field unchanged.

The anonymous request still contains only `HNHBK`, `HKIDN`, `HKVVB` and `HNHBS`.

## Ingress navigation correction

Both registration-storage and probe POSTs now redirect relatively to the App root. They no
longer send `Location: /`, so Home Assistant's root dashboard cannot be loaded inside the
DKB Ingress iframe by these actions.

## Bounded persistent diagnostics

Probe-state schema 2 persists only sanitized capability/failure metadata. It distinguishes
successful BPD results, valid bank responses without BPD, non-success HTTP status,
transport failure, strict-protocol failure and bounded local failure categories.

A syntactically valid FinTS response containing bounded `HIRMG`/`HIRMS` return codes but no
`HIBPA` is now classified as `bank_rejected` rather than discarded as a generic protocol
error. Unique bounded four-digit return codes and bounded sanitized message text from those
recognized return-message structures survive for operator diagnosis. The configured 25-character
product registration is redacted if echoed, arbitrary/unknown segment payload is never persisted,
and the decoded response contributes only its SHA-256 and byte count before the raw response is
discarded.

The UI may state that propagation of a newly issued registration is **one possible cause**
of a valid bank rejection without BPD. It does not claim that interpretation unless the
sanitized evidence proves it.

Successful schema-1 probe evidence from earlier releases remains loadable.

## Future architecture recorded

The roadmap now explicitly records two broader reusable-PA goals exposed by recent live
work:

- user-configurable target architecture, so the current seven-ETF retirement plan remains
  one user's configuration rather than a product assumption; and
- a first-class dynamic presentation model that can render configured targets and all
  outside-scope holdings without hard-coded entity lists or custom frontend dependencies.

These are future architectural milestones and are not implemented by v1.31.2.

## Preserved boundaries

- v1.31 canonical Robotics target and superseded-exception history: unchanged
- v1.31.1 ISIN-only outside-scope holding hotfix: unchanged
- broker schema 2 and provider-aware execution evidence: unchanged
- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported
- provider acquisition and multi-source aggregation: unchanged
- v1.27 private-PKI verified HTTPS, bearer authentication, Supervisor trust discovery,
  DNS pinning and no-plaintext fallback: unchanged
- Comdirect OAuth/session maintenance: unchanged
- Trade Republic statement import/private snapshot behavior: unchanged; this release does not move PDF parsing into Portfolio Architect
- DKB remains experimental/manual-only/non-live; authenticated user-capability/UPD and
  DKB-App decoupled authentication remain later gates before any holdings implementation
- DKB live Gateway acquisition remains a later authenticated milestone
- No trading, order, transfer, payment, or transaction-history capability is added
- no automatic sell capability is added

The historical `v1.19.0-rc2` experimental brokerage probe remains excluded and is not promoted by this release.

The integration and all three official Gateway Apps are version-aligned to 1.31.2. The
functional runtime change is confined to the DKB capability-probe App.

See `docs/UPGRADE-1.31.2.md`.
