# Portfolio Architect 1.29.0

Version 1.29.0 is a presentation-only milestone prepared from the exact published and
live-accepted v1.28.2 baseline. It refines the native Home Assistant policy-compliance
reference dashboard without changing Portfolio Architect calculations, entities,
provider acquisition, Gateway runtime or wire contracts.

## Policy-compliance visual hierarchy

The accepted-exception lifecycle is already a governed state rather than a policy
failure: the dashboard shows the accepted exception count, the concrete Robotics
exception, the decision date and the next/overdue review date as one coherent block.
The four savings-plan fee findings below it are different: they are non-critical
optimisation opportunities.

Version 1.29.0 makes that distinction visible by inserting one native conditional
Heading card between those two groups:

- English: **Optimisation opportunities**
- German: **Optimierungsmöglichkeiten**
- style: native Home Assistant `subtitle`
- icon: `mdi:lightbulb-on-outline`
- visibility: only while `sensor.portfolio_architect_optimisation_opportunity_count`
  is greater than zero
- badge: the existing optimisation-opportunity count, shown as a compact native entity
  badge with normal more-info interaction

The subtitle disappears completely when there are no optimisation opportunities.

## Preserved dashboard contracts

The existing green mandatory-controls banner is unchanged. The accepted-exception
count, Robotics exception, last decision and next/overdue review tiles are unchanged.
The four concrete fee-opportunity tiles remain blue, full-width and individually
inspectable through Home Assistant more-info.

No custom card, JavaScript, CSS/card-mod or Markdown card is added. The reference
layout continues to use native Home Assistant dashboard primitives only.

The optimisation-opportunity count remains an existing native entity; v1.29.0 does
not create a new entity or change its value semantics. It is surfaced only as the
small heading badge and does not become another primary tile.

## Runtime and security invariants

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported
- entity IDs, unique IDs and machine-readable states: unchanged
- policy evaluation and accepted-exception semantics: unchanged
- portfolio calculations and execution recommendations: unchanged
- source atomicity and LKG behavior: unchanged
- v1.27 private-PKI verified HTTPS and bearer authentication: unchanged
- Comdirect v1.27.4 OAuth/session maintenance: unchanged
- Trade Republic statement import: unchanged
- v1.28 DKB FinTS registration/capability-probe gate: unchanged
- No trading, order, transfer, payment, or transaction-history capability is added
- the historical `v1.19.0-rc2` experimental brokerage probe is not promoted by this release

DKB live Gateway acquisition remains a later authenticated milestone. Trade Republic statement import remains provider-isolated; this release does not move PDF parsing into Portfolio Architect.

## Dashboard update

The reference dashboard is static user-owned Home Assistant configuration after it is
imported. HACS does not overwrite an existing dashboard. Therefore users who want the
v1.29.0 presentation polish must deliberately apply the updated reference YAML or
merge the documented policy-section change into their existing dashboard.

See `docs/UPGRADE-1.29.0.md`.
