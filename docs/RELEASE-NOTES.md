# Portfolio Architect 1.20.1

Version 1.20.1 is a focused maintenance release for the graceful-degradation behavior introduced in 1.20.0.

## Entity propagation during LKG

Version 1.20.0 could correctly enter Home Assistant last-known-good mode internally while ordinary coordinator entities remained frozen in their previous live state. The coordinator returned the same trusted `PortfolioData`, and `always_update=False` therefore suppressed listener callbacks even though LKG, Gateway health, integrity, and plan-actionability metadata had changed.

Version 1.20.1 removes that invalid equality optimization. Every completed coordinator update cycle notifies listeners, so entering LKG immediately publishes the degraded state. Informational holdings, quantities, valuation, allocation, and policy data may remain visible from the trusted cache, while authorized investment cash, recommendations, fees, cash outlay, and plan actionability become unavailable/non-actionable as designed. The same notification rule applies when the source recovers back to live operation.

## Integrity Repair lifecycle

Integrity failures remain fail-closed and continue to preserve the previously accepted snapshot. Version 1.20.1 also makes the integrity error reason specific to the current degraded refresh path: an unrelated transport, rate-limit, supplemental-source, or calculation fallback does not republish an older integrity-failure reason. Actual timestamp regression or snapshot-integrity validation failures explicitly preserve their integrity status while LKG is served.

Regression coverage also confirms that a Gateway in `reauthentication_required` mode continues to describe its cached snapshot with the same generated timestamp, SHA-256 fingerprint, and position count.

## Compatibility

Payload schema 8, REST schema 1, Gateway health schema 5, entity IDs, unique IDs, cash-authorization semantics, LKG retention limits, and the read-only Gateway API surface are unchanged. Gateway runtime behavior is unchanged apart from the package version; the new reauthentication test protects the existing health contract.

No trading, order, transfer, payment, or transaction-history capability is added.
## Experimental branch note

The historical `v1.19.0-rc2` tag remains a separate experimental brokerage-diagnostics branch. Stable 1.20.1 does **not** promote those experimental diagnostics.

