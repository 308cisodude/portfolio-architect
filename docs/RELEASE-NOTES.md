# Portfolio Architect 1.21.0

Version 1.21.0 is an execution-semantics and clarity release. It does not add trade execution or transaction-history capability.

## Scheduled execution is context, not evidence

The existing `sensor.portfolio_architect_planned_execution` entity keeps its entity ID and date value for compatibility, but its display name is now **Scheduled execution**. A scheduled date may legitimately be in the past while a recommendation remains valid. The date therefore describes the plan cycle that the latest evaluation was prepared for; it is not proof that an order was placed, that a transaction occurred, or that the recommendation automatically expired.

## Current actionability

A new `sensor.portfolio_architect_plan_actionability` exposes the current relationship between source trust, execution readiness, and schedule timing. Its bounded states are:

- `scheduled` — the source is actionable, the execution state is ready, and the scheduled date is still ahead;
- `actionable_now` — the plan is ready and the scheduled date is today, or no recurring execution schedule is configured;
- `overdue_actionable` — the scheduled date has passed but the current trusted recommendation is still actionable;
- `not_ready` — the source is actionable but the execution state is not ready;
- `not_actionable` — freshness, LKG, integrity, reauthentication, or Gateway health prevents a new investment action.

Attributes expose the last evaluation timestamp, scheduled execution date, schedule relation, days until the scheduled date, execution state, and the existing bounded actionability reason. This is advisory state only; it does not infer transaction history.

## Dashboard and freshness wording

The reference dashboard now presents **Scheduled execution**, **Actionability**, and **Last evaluated** as separate concepts. Runtime health also labels the existing freshness binary sensor as **Snapshot freshness** and shows its translated state (**Within freshness window** / **Outside freshness window**). This makes the v1.20 LKG state coherent: a live source can be unavailable while a previously validated snapshot remains inside its allowed freshness window.

## Compatibility

Payload schema 8, REST schema 1 (portfolio), Gateway health schema 5, existing entity IDs, existing unique IDs, cash-authorization semantics, LKG retention, and the read-only Gateway API surface are unchanged. The Gateway package is version-aligned to 1.21.0; its banking runtime behavior is unchanged.

No trading, order, transfer, payment, or transaction-history capability is added. A quantity change remains a holdings observation, not proof of a trade.

## Experimental branch note

The historical `v1.19.0-rc2` tag remains a separate experimental brokerage-diagnostics branch. Stable 1.21.0 does **not** promote those experimental diagnostics.
