# Portfolio Architect 1.18.0

Version 1.18.0 adds **Plan Delta & Decision Trace**. Portfolio Architect can now
explain what materially changed between the two most recent fresh, validated
portfolio evaluations without inferring trades or retaining transaction history.

## Two-evaluation decision trace

- Adds `sensor.portfolio_architect_plan_change` as a translated bounded enum.
- Retains exactly the previous and current provider-neutral evaluation snapshots
  in private, atomic Home Assistant storage with canonical SHA-256 validation.
- Restores the last trace across integration reloads and Home Assistant restarts.
- Does not advance the trace when the REST source falls back to the existing
  Home Assistant last-known-good calculation.

## Deterministic change classification

The trace distinguishes:

- allocation changes;
- recommendation changes;
- execution-state or investment-cash changes;
- policy changes;
- source-composition changes; and
- combined changes.

Per-position attributes expose stable reason codes such as
`entered_target_corridor`, `left_target_corridor`,
`proposed_purchase_removed`, and `recommendation_reason_changed`.

To avoid refresh noise, drift-only changes below 0.10 percentage points and
non-zero purchase changes below EUR 1.00 are not reported as material. Status
transitions and additions/removals remain visible regardless of those thresholds.

## Native bilingual dashboard

The supplied English/German dashboard adds one full-width conditional tile named
**Changes since previous evaluation / Änderungen seit letzter Auswertung**. The
tile remains hidden for the initial baseline, unchanged evaluations, and
unavailable state. It opens the native more-info dialog; no custom card or
JavaScript dependency is introduced.

## Privacy and safety

- No raw source document, account identifier, ISIN, WKN, credential, OAuth
  material, or transaction history is stored in the trace.
- The trace never claims that a recommended order was executed.
- Persistence is non-authoritative: a trace-storage failure cannot suppress or
  alter the validated portfolio calculation.
- Detailed trace attributes are excluded from recorder history; only the bounded
  enum state is eligible for normal state-history recording.
- Diagnostics expose only trace state, timestamps, categories, counts, and stable
  fund IDs; monetary deltas remain in the current entity state, not diagnostics.

## Compatibility

- No configuration-entry migration.
- Payload schema 8, REST schema 1, and Gateway health schema 5 remain unchanged.
- No allocation corridor, policy, or cost-model change.
- Existing entity IDs and unique IDs remain unchanged; one new entity is added.
- Gateway App 1.16.1 and later remain protocol-compatible. The 1.18.0 Gateway
  package aligns release metadata only.
- Replacing the dashboard YAML is optional for runtime compatibility and required
  only to show the new conditional trace tile.
