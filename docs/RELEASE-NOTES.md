# Portfolio Architect 1.34.1

Version 1.34.1 is a narrow Home Assistant presentation-correctness hotfix based on the
live-accepted v1.34.0 generic target architecture.

## Whole-portfolio allocation entities

Every configured target now owns its established `*_whole_portfolio_allocation` entity from
target state, whether or not a current holding exists. A missing target therefore remains
available at `0%` instead of leaving a dashboard distribution reference unresolved. Existing
held target entity IDs and unique IDs are preserved.

Outside-current-plan holdings continue to receive whole-portfolio allocation entities only from
accepted holding evidence. Their lifecycle remains evidence-driven.

## ISIN-first reference-dashboard bindings

The v1.34.0 Phase-B reference dashboard still contained seven pre-ISIN-migration WKN-era
outside-holding allocation IDs. Version 1.34.1 replaces those references with the established
ISIN-first holding IDs. The distributing Robotics reference was already ISIN-first and remains
unchanged.

The dashboard's outside-current-plan detail Tile inventory remains intentionally static for this
hotfix. The first-class v1.34 presentation model remains the complete current-state inventory and
is the backend contract for the later dynamic native-dashboard milestone.

## Compatibility invariants

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported
- v1.33.0 source-freshness and plan-schedule separation remains preserved
- v1.33.1 recurring scheduling remains anchored to the latest valid Portfolio Architect evaluation

No trading, order, transfer, payment, or transaction-history capability is added. No automatic
sell capability is added.

## Preserved contracts

- Portfolio payload schema 8: unchanged.
- REST portfolio schema 1: unchanged.
- Gateway health schema 6: unchanged; schemas 1–5 remain supported.
- v1.33.0 source-freshness and plan-schedule separation remains preserved; evidence-kind source
  freshness is unchanged. v1.34.1 does not change any configured freshness threshold.
- v1.33.1 evaluation-anchored recurring scheduling remains anchored to the latest valid Portfolio
  Architect evaluation.
- Portfolio schema 2 opaque 128-bit target identity and schema-1 compatibility are unchanged.
- Presentation schema 1 is unchanged.
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
- Provider-owned authorized-cash policy and current execution-routing behavior are unchanged.
- No trading, order, transfer, payment, or transaction-history capability is introduced. No
  automatic sell capability is introduced either.

See `docs/UPGRADE-1.34.1.md`.
