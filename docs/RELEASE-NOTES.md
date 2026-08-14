# Portfolio Architect 1.26.5

Version 1.26.5 is a narrow Home Assistant presentation hotfix after v1.26.4 live
acceptance. Version 1.26.4 correctly kept schedule/policy values as native
`SensorDeviceClass.DATE` sensors, but the Home Assistant frontend does not apply a
Tile `time_format` override to that sensor class. The visible Tiles therefore still
showed raw ISO `YYYY-MM-DD` states.

## Native date-domain presentation

The five established sensors remain unchanged and authoritative:

- `sensor.portfolio_architect_planned_execution`
- `sensor.portfolio_architect_next_plan_review`
- `sensor.portfolio_architect_last_exception_decision`
- `sensor.portfolio_architect_next_exception_review`
- `sensor.portfolio_architect_oldest_overdue_exception_review`

Version 1.26.5 adds matching Home Assistant `date`-domain presentation entities:

- `date.portfolio_architect_planned_execution`
- `date.portfolio_architect_next_plan_review`
- `date.portfolio_architect_last_exception_decision`
- `date.portfolio_architect_next_exception_review`
- `date.portfolio_architect_oldest_overdue_exception_review`

Each counterpart mirrors the same Python `date` value. It does not format a string,
convert through UTC/local time, or synthesize a timestamp. Home Assistant therefore
handles visible localization through its normal `date`-domain state formatter.

Reference-dashboard Tiles use the new `date.*` entities only for display. Existing
conditional logic, automations, templates, recorder/API consumers, and Portfolio
Architect calculations can continue to use the unchanged authoritative sensors.

## Read-only boundary

Home Assistant's `date` domain normally supports `date.set_value`. Portfolio
Architect's presentation counterparts are intentionally read-only and reject every
write attempt. Each reference Tile routes `more-info` to the corresponding authoritative
`sensor.*` entity instead of opening the presentation `date.*` entity. This preserves
the established inspection UX without exposing the date domain's normal editable
input control. No Portfolio Architect plan or policy value can be changed through
these entities.

## Removed v1.26.4 workaround

The affected date-only Tiles no longer carry `state_content: state` plus
`time_format: {type: date, style: short}`. That configuration was valid Tile YAML
but did not enter Home Assistant's date formatter for a `sensor` domain entity.
Refresh-schedule timestamp Tiles remain unchanged on their established native
`datetime` / `short` formatting.

## Compatibility

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported
- all existing `sensor.*` and `binary_sensor.*` entity IDs / unique IDs: unchanged
- five additive read-only `date.*` presentation entities
- provider acquisition/authentication/private state: unchanged
- Comdirect authorized-cash semantics: unchanged
- Trade Republic statement import/persisted snapshot: unchanged
- DKB Gateway: still experimental/manual-only/fail-closed, no acquisition path
- no trading/order/transfer/payment/transaction-history capability

DKB live Gateway acquisition remains a later provider-specific milestone; v1.26.5 does not promote the experimental DKB shell into a live acquisition source.

This release does not move PDF parsing into Portfolio Architect; Trade Republic statement parsing remains isolated in the Trade Republic Gateway App.

No trading, order, transfer, payment, or transaction-history capability is added by this release.

The historical experimental `v1.19.0-rc2` brokerage diagnostics/fee-probe work
remains separate and is not promoted by this release.

Gateway HTTPS transport hardening remains the next security milestone in v1.27.0.
