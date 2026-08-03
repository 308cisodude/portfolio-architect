# Plan delta and decision trace

Portfolio Architect 1.18.0 records a bounded comparison between the two most
recent **fresh, validated** portfolio evaluations. The trace is derived inside
Home Assistant after the normal source, calculation, and payload validation
boundaries have succeeded.

## Purpose

The trace answers three operational questions without reconstructing transaction
history:

- what materially changed since the previous evaluation;
- which target positions entered or left the allocation corridor; and
- why a recommendation, execution state, policy result, or source composition
  changed.

It does not claim that a recommendation was executed. A holding can change due to
market movement, an external purchase, a transfer, or a changed source document.
The trace therefore uses neutral statements such as `holding changed`,
`recommendation changed`, and `entered_target_corridor`.

## Home Assistant entity

`sensor.portfolio_architect_plan_change` is a translated enum with these bounded
states:

- `baseline_established`;
- `unchanged`;
- `allocation_changed`;
- `recommendation_changed`;
- `execution_state_changed`;
- `policy_changed`;
- `source_changed`;
- `multiple_changes`.

Its attributes contain stable reason codes and bounded structured values. They do
not contain free-form source messages, raw portfolio documents, credentials, bank
account identifiers, or transaction history. The current attributes remain available
in Home Assistant but are explicitly excluded from recorder history; only the bounded
enum state is recorded over time.

## Material-change thresholds

Minor numeric movement is suppressed from the position-change list:

- allocation drift must change by at least **0.10 percentage points** unless the
  allocation status itself changes;
- a non-zero purchase recommendation must change by at least **EUR 1.00** unless
  the recommendation is added or removed.

Status, reason, route, deferral, source, and policy transitions are always
reported. The thresholds are fixed contract values exposed in the entity
attributes; they are not financial-advice settings.

## Position reason codes

Examples include:

- `entered_target_corridor`;
- `left_target_corridor`;
- `material_drift_changed`;
- `proposed_purchase_added`;
- `proposed_purchase_removed`;
- `proposed_purchase_changed`;
- `recommendation_reason_changed`;
- `execution_route_changed`;
- `position_execution_state_changed`;
- `deferral_state_changed`.

Each change row is keyed by the stable plan `fund_id` and includes only the
previous/current bounded decision values required for explanation.

## Persistence and failure semantics

The private Home Assistant store contains exactly two provider-neutral evaluation
snapshots. It is atomic, size-bounded, protected by a canonical SHA-256 integrity
value, and strictly revalidated when restored.
It stores no ISIN, WKN, account number, IBAN, credentials, OAuth material, raw
source rows, or source paths.

A REST last-known-good replay is not a fresh evaluation and therefore never
advances the trace. If trace persistence fails, portfolio calculation and entity
publication continue; the trace is non-authoritative advisory metadata.

## Dashboard behavior

The supplied English/German dashboard adds one native conditional tile. It is
hidden while the baseline is being established, when no material change exists,
or when the entity is unavailable. Selecting the tile opens Home Assistant's
native more-info dialog with the bounded trace attributes.
