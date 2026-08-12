# Portfolio Architect 1.20.0

Version 1.20.0 adds graceful degradation and trustworthy freshness semantics for
live REST portfolios. It is designed around one rule: **trusted stale data may
remain useful for information, but it must not silently authorize a new
investment action**.

## Graceful last-known-good operation

Portfolio Architect already stored one private, validated last-known-good (LKG)
calculation. Version 1.20.0 makes that cache an explicit availability boundary.
When the Gateway becomes unreachable, a supplemental source fails, calculation
cannot complete, or a newly received snapshot fails integrity/timestamp checks,
PA can continue serving the previously validated calculation while it remains
inside the bounded retention window.

The retention limit uses the positive maximum-cache age advertised by the
Gateway when available and otherwise falls back to seven days. The cache remains
bound to the endpoint and current portfolio configuration; a configuration change
cannot silently reuse a calculation produced for different inputs.

A rejected incoming snapshot never replaces the accepted fingerprint, position
count, timestamp, or calculation. Integrity failures remain visible as errors even
while the older trusted portfolio remains available.

## Informational data versus actionable planning

A degraded/LKG portfolio can continue to expose holdings, quantities, valuation,
allocation, architecture, and policy information. Investment actions require
stronger evidence.

For REST sources, a plan is actionable only when:

- the accepted portfolio is within the configured data-freshness window;
- the active data is not Home Assistant LKG;
- no snapshot-integrity error is active;
- Gateway health is available;
- reauthentication is not required; and
- the effective Gateway operating mode is `live`.

When those requirements are not met, stale authorized cash, proposed purchases,
purchase explanations, recommended totals, fees/outlay, reserve-derived execution
state, and purchase counts become unavailable. Configuration facts such as plan
budget, frequency, and execution policy remain visible. This prevents cached bank
cash from acting as current authorization.

## Evidence-based refresh-overdue detection

Version 1.19.1 could produce a false `refresh_overdue` alarm when the Portfolio
Architect 15-minute poll happened shortly before the Gateway's 15-minute refresh.
The locally ticking diagnostic later crossed the old deadline even though the
Gateway had refreshed successfully in the meantime.

Version 1.20.0 records when Gateway health was actually observed. A refresh can be
reported overdue only when a health document obtained at or after the deadline
plus grace still proves the missed refresh. An older health sample may show
`due_now`, but it cannot become failure evidence merely because local time moves
forward.

Snapshot age and retention countdown are likewise derived locally from the
accepted snapshot timestamp instead of displaying an integer frozen at the last
REST poll. Their entities refresh on the existing minute tick without adding
another bank or portfolio poll.

## AI-assisted development disclosure

Portfolio Architect is developed with substantial use of generative AI for
implementation, tests, documentation, review assistance, and release preparation
under maintainer direction. `AI_POLICY.md` documents the actual project workflow,
including human-controlled publication and maintainer responsibility.

Portfolio Architect is not an Open Home Foundation project and does not claim
compliance with the Open Home Foundation AI Policy. The OHF policy informs the
project's accountability and human-in-the-loop principles.

## Compatibility

Payload schema 8, REST schema 1, Gateway health schema 5, entity IDs, unique IDs,
authorized-cash semantics, authentication state, and the provider-neutral data
contract are unchanged. The Gateway runtime protocol is unchanged; its package
version is aligned to 1.20.0 for release consistency.

No trading, order, transfer, payment, transaction-history, or new brokerage-provider
capability is added. The historical `v1.19.0-rc2` brokerage-diagnostics branch remains separate. Stable
1.20.0 does **not** promote those experimental diagnostics.
