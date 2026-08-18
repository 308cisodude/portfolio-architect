# Portfolio Architect 1.34.0

Version 1.34.0 is the **generic portfolio target architecture and first-class current-state
presentation-model** milestone, prepared from the exact live-accepted v1.33.1 baseline.

## Opaque 128-bit target identity

Portfolio-definition schema 2 introduces explicit `target_id` values. A schema-2 target ID is
`target_` followed by 32 lowercase hexadecimal digits generated from 128 random bits.

The target ID represents one currently configured strategic role. It is deliberately independent
from ISIN, WKN, display name, list order, target weight and purchase eligibility. The native plan
editor generates the ID once when a new target role is created and persists it with that role.
Users do not have to derive or type an identity from a security name or identifier.

ISIN remains the canonical instrument identity. WKN remains secondary fallback/validation
metadata and never participates in target-ID generation. The native plan editor now keys
candidate selection by ISIN and shows WKN only as secondary metadata.

Schema 1 remains supported for existing installations and historical UI overrides. Legacy human-
readable `id` values continue to canonicalize as compatibility target identity there. Schema 2 is
stricter: an explicit opaque 128-bit `target_id` is required. `fund_id` / `plan_fund_id` remain
payload-schema-8 compatibility aliases for the same target identity.

## Current-state lifecycle

Portfolio Architect remains about **the portfolio now and the next investment cycle**, not target
history.

Deleting a target removes that current strategic role. PA does not keep a tombstone or retired-
target database. If the same ISIN is introduced as a target again later through PA, a fresh target
ID is generated rather than resurrecting the old role.

Outside-current-plan holdings have no configured target identity. They exist only while accepted
source evidence reports them. Once all relevant accepted sources supersede the holding with data
that no longer contains it, it disappears automatically from the whole-portfolio and presentation
model. Source failure, old still-accepted evidence, or LKG state is never interpreted as a sale.

## Generic bounded plans

Plans remain bounded to at most 32 positive-weight targets. The reference seven-ETF plan is now
only example configuration. Its schema-2 migration uses opaque IDs generated through the same PA
target-ID generator and therefore intentionally performs a one-time target-entity identity
migration from the historical semantic IDs.

The supplied reference dashboard is aligned to the migrated opaque IDs. Existing imported user
dashboards are never overwritten automatically.

## First-class structural presentation model

A diagnostic `presentation_model` sensor exposes presentation schema 1 as a bounded current-state
structural index. It contains:

- configured targets with stable target/entity keys and source provenance;
- current-plan holding identities and target relationships;
- every currently evidenced outside-current-plan holding with stable ISIN-first holding identity;
- bounded plan-actionability and policy-summary state.

It deliberately excludes quantities, values, proposed purchase amounts and other high-churn data
already represented by dedicated native entities. It also contains no bank-account, credential or
provider-authentication material.

This is the backend contract for a later dynamic native-dashboard milestone. v1.34.0 adds no
`auto-entities`, card-mod, custom JavaScript or other custom frontend dependency.

## Presentation wording

The ambiguous policy tile **Next review** becomes **Exception review** (German:
**Ausnahmeprüfung**) so it cannot be confused with the independent **Next plan review** schedule.

## Preserved runtime/provider contracts

- Portfolio payload schema 8: unchanged.
- REST portfolio schema 1: unchanged.
- Gateway health schema 6: unchanged; schemas 1–5 remain supported.
- v1.33.0 source-freshness and plan-schedule separation remains preserved; evidence-kind source freshness is unchanged. v1.34.0 does not change any configured freshness threshold.
- v1.33.1 evaluation-anchored recurring scheduling remains anchored to the latest valid Portfolio Architect evaluation.
- Comdirect acquisition/OAuth/session/PhotoTAN/cash unchanged.
- Trade Republic statement import/private diagnostics unchanged; PDF parsing remains provider-side
  and memory-only.
- DKB registered anonymous FinTS probe unchanged. DKB live Gateway acquisition remains a later
  provider-specific milestone; DKB remains experimental/manual-only/non-live and authenticated
  user-capability/UPD remains a later gate.
- This release does not move PDF parsing into Portfolio Architect; Trade Republic statement PDF
  parsing remains isolated provider-side and memory-only.
- Private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-
  plaintext fallback unchanged.
- Historical v1.19.0-rc2 brokerage probe remains excluded and is not promoted by this release.
- No trading, order, transfer, payment, or transaction-history capability is introduced. No automatic sell capability is introduced either.

See `docs/TARGET-ARCHITECTURE.md` and `docs/UPGRADE-1.34.0.md`.
