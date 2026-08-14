# Portfolio Architect 1.26.3

Version 1.26.3 is a low-risk dashboard/presentation follow-up to v1.26.2. It closes
the remaining German unavailable-state display edge case found during live
acceptance and simplifies the policy-compliance section without changing portfolio
calculation, provider acquisition, wire schemas, or machine-readable entity
contracts.

## German unavailable-state presentation

Home Assistant does not render an entity attribute through a Tile card once that
entity itself becomes unavailable. That affected the always-visible German
**Zugeordnet** and **Käufe** tiles during degraded/non-actionable LKG operation even
though the underlying entities exposed `display_state_de: Nicht verfügbar`.

Version 1.26.3 preserves the existing availability semantics of
`sensor.portfolio_architect_recommended_total` and
`sensor.portfolio_architect_purchase_count`. Instead, the always-available
`sensor.portfolio_architect_plan_actionability` entity exposes bounded presentation
proxies:

- `recommended_total_display_de`; and
- `purchase_count_display_de`.

The German reference dashboard uses those attributes for display and keeps the tile
more-info action pointed at the original monetary/count entity. Machine-readable
states, availability semantics, IDs, and recorder/API contracts remain unchanged.

## Policy-compliance dashboard simplification

The primary policy dashboard no longer renders the aggregate **Checks** and
**Opportunities** counters. Their native entities remain available unchanged for
diagnostics, templates, automations, and API consumers. Concrete optimisation
opportunity tiles remain visible, so actionable information is not removed.

The accepted-exception lifecycle is now grouped coherently:

- **Exceptions** beside **Robotics exception**;
- **Last decision** beside **Next review**; and
- when a review is overdue, the date tile is labelled **Overdue review**.

The German equivalents are **Ausnahmen**, **Robotik-Ausnahme**, **Letzte
Entscheidung**, **Nächste Prüfung**, and **Überfällige Prüfung**. Conditional policy error/warning tiles remain available and are
shown ahead of the exception lifecycle when attention is required.

## Compatibility and security

The established compatibility baseline remains **payload schema 8**, **REST portfolio schema 1**, and **Gateway health schema 6**; schemas 1–5 remain supported.
The historical experimental `v1.19.0-rc2` brokerage diagnostics/fee-probe work remains separate and is not promoted by this release.
No trading, order, transfer, payment, or transaction-history capability is added.
DKB live Gateway acquisition remains a later provider-specific milestone; v1.26.3 does not promote the experimental DKB shell into a live acquisition source.
This release does not move PDF parsing into Portfolio Architect; Trade Republic statement parsing remains isolated in the Trade Republic Gateway App.

- payload schema: 8 (unchanged)
- REST portfolio schema: 1 (unchanged)
- Gateway health schema: 6 (unchanged; health schemas 1-5 remain supported)
- existing entity IDs / unique IDs: unchanged
- machine-readable entity states and availability contracts: unchanged
- v1.26.2 unavailable-source diagnostics: unchanged
- v1.26.1 ISIN-first identity and WKN fallback: unchanged
- v1.26 atomic configured-source/LKG behavior: unchanged
- Comdirect authorized-cash semantics: unchanged
- Trade Republic statement import and persisted snapshot: unchanged
- DKB Gateway remains an experimental manual-only fail-closed shell
- no trading, order, transfer, payment, or transaction-history capability

The release adds no private identifiers or transport metadata to dashboard
presentation. The existing privacy/publication gates remain authoritative.

Gateway HTTPS transport hardening remains the next security milestone in v1.27.0.
