# Upgrade to Portfolio Architect 1.21.0

Version 1.21.0 separates execution scheduling from current actionability and clarifies snapshot-freshness wording.

## What changes

- `sensor.portfolio_architect_planned_execution` keeps its entity ID and unique ID, but its display name becomes **Scheduled execution**.
- New `sensor.portfolio_architect_plan_actionability` states whether the current recommendation is scheduled, actionable now, overdue but still actionable, not ready, or not actionable.
- The reference dashboard adds **Actionability** and **Last evaluated** next to the scheduled execution context.
- `binary_sensor.portfolio_architect_data_fresh` keeps its entity ID and boolean semantics; its display wording now explicitly refers to the snapshot freshness window.

A past scheduled execution date does not by itself expire a recommendation and is never treated as transaction evidence. Source freshness, integrity, LKG state, Gateway health, and execution readiness remain authoritative for actionability.

## Upgrade procedure

1. Update **Portfolio Architect Gateway** to 1.21.0 through **Settings → Apps**.
2. Update **Portfolio Architect** to 1.21.0 through HACS.
3. Restart Home Assistant after the HACS update.
4. Confirm `Version` reports 1.21.0 and normal live health is healthy.
5. Confirm `sensor.portfolio_architect_plan_actionability` exists. If the scheduled execution date is already in the past while the plan remains ready and live, the actionability state should be `overdue_actionable`.

No reauthentication, entity migration, configuration change, or dashboard replacement is required for existing installations. Users who maintain a copied reference dashboard may import the updated dashboard YAML to receive the new labels/cards.

## Compatibility

- payload schema: 8 (unchanged)
- REST portfolio schema: 1 (unchanged)
- Gateway health schema: 5 (unchanged)
- existing entity IDs / unique IDs: unchanged
- new entity: `sensor.portfolio_architect_plan_actionability`
- authorized-cash and LKG semantics: unchanged
- no transaction-history or trade-execution semantics
