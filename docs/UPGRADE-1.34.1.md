# Upgrade to Portfolio Architect 1.34.1

Version 1.34.1 fixes two Home Assistant presentation defects discovered during live acceptance of
the v1.34.0 opaque-target migration. It does not change portfolio strategy, source configuration,
provider acquisition, wire schemas, cash authorization or execution policy.

## Upgrade order

1. Update **Portfolio Architect** through HACS to 1.34.1 and restart Home Assistant once.
2. Keep the existing schema-2 `portfolio.yaml`, `instruments.yaml`, `broker.yaml`,
   `exceptions.yaml`, source configuration, freshness thresholds and recurring schedule unchanged.
3. Replace or merge the v1.34.1 reference dashboard if you use the copied reference dashboard.
   This updates outside-scope distribution entity references to their ISIN-first holding IDs.
4. Confirm the missing accumulating Robotics target renders in whole-portfolio distribution with
   its friendly name and `0%` allocation.
5. Confirm outside-scope distribution entries referenced by the dashboard show their current
   percentages rather than `Unavailable`.
6. Update the Comdirect, Trade Republic and DKB Gateway Apps to 1.34.1 in place for package
   alignment. Do not remove App-private data. Do not reauthenticate Comdirect, re-import Trade
   Republic, or re-probe DKB solely because of this hotfix.

No plan/schema migration is introduced by this hotfix. The one-time schema-2/opaque-ID migration
was the v1.34.0 Phase-B migration and must not be repeated.

## What was fixed

A target's whole-portfolio share is defined even when the target is currently missing. v1.34.0
created `*_whole_portfolio_allocation` only from actual holdings, leaving a missing target's
reference unresolved. v1.34.1 creates the established entity from target state for every
configured target, so a missing target reports `0%` while held targets retain their existing
entity identity.

The v1.34.0 reference dashboard also retained seven old WKN-era outside-holding allocation IDs.
v1.34.1 points those distribution entries at the established ISIN-first holding IDs. No provider
or portfolio data was missing; this was a dashboard-reference defect.

## Deliberately unchanged

The outside-current-plan detail Tile inventory is still static. v1.34.1 corrects the existing
ISIN-first bindings for that static inventory, while `sensor.portfolio_architect_presentation_model`
remains the complete dynamic outside-scope inventory. Dynamic native outside-scope Tile
presentation remains a later milestone.

The provider-scoped cash/funding-topology work discussed after v1.34 live acceptance is likewise
not part of this hotfix. Current authorized-cash and execution-routing semantics are unchanged.

## Preserved boundaries

- portfolio schema 2 and opaque 128-bit target identity unchanged; schema 1 compatibility retained
- presentation schema 1 unchanged
- payload schema 8 unchanged
- REST portfolio schema 1 unchanged
- Gateway health schema 6 unchanged
- source freshness and recurring scheduling unchanged
- Comdirect/Trade Republic/DKB provider behavior unchanged
- DKB registration-gated anonymous FinTS probe unchanged; it performs no holdings acquisition and live DKB holdings remain disabled
- `HIWPDS` remains bank-level capability evidence only; authenticated user-capability/UPD remains a later gate
- private-PKI HTTPS/bearer/DNS/no-plaintext-fallback unchanged
- no trading, order, automatic sell, transfer, payment or transaction-history capability
