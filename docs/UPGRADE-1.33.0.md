# Upgrade to Portfolio Architect 1.33.0

Version 1.33.0 separates provider-evidence freshness from recurring plan scheduling and adds
explicit bounded evidence-kind freshness policy. It also fixes the live-discovered
`Restore file-based plan` defect that removed execution/review schedule options together with
the Home Assistant target-plan override.

## Upgrade order

1. Update **Portfolio Architect** through HACS to 1.33.0 and restart Home Assistant once.
2. Update **Portfolio Architect Gateway — Comdirect**, **— Trade Republic**, and **— DKB** to
   1.33.0 in place, preserving each App-private `/data` volume.
3. Do not reauthenticate Comdirect merely because of this release when the current session is healthy.
4. Do not re-import the Trade Republic statement merely because of this release.
5. Do not re-enter the DKB FinTS product registration or run another DKB probe merely because
   of this release.
6. No dashboard replacement is required; the v1.32 stale-source detail already renders each
   source's effective threshold.

There is no portfolio-plan, config-entry, bank-authentication or Gateway-wire migration.

DKB remains at the existing FinTS research gate. `HIWPDS` is still only bank-level capability
evidence; authenticated user capability/UPD validation and DKB-App decoupled authentication
remain later requirements before any holdings implementation. No holdings acquisition is enabled by v1.33.0.

## Conservative freshness migration

The software upgrade alone **must not make a stale plan actionable**.

Pre-v1.33 installations have one stored `freshness_hours` value. Until the operator
explicitly saves the new evidence-kind settings, v1.33 applies that existing value to every
source category. An installation using 168 hours therefore remains equivalent immediately
after upgrade: the old DKB CSV remains stale and the plan remains non-actionable.

The new **Configure → Runtime safeguards** page can then set independent limits for:

- live API / provider Gateway snapshots: 1–168 hours;
- imported statements: 1–744 hours;
- imported CSV evidence: 1–744 hours; and
- other/unknown source evidence: 1–168 hours.

These are user-owned policy values. Portfolio Architect does not silently infer that a CSV or
statement deserves a longer lifetime merely because of its provider category.

A deliberately selected example profile for a mixed live/document portfolio could be:

```text
Live API / Gateway snapshots: 24 h
Imported statements:          168 h (7 days)
Imported CSV:                  744 h (31 days)
Other sources:                 24 h
```

This is an example, not an automatic migration or product assumption.

## Source freshness is independent of review scheduling

Beginning with v1.33, `binary_sensor.portfolio_architect_data_fresh` is determined solely by
contributing source evidence and its effective evidence-kind thresholds.

A future `next_review_on` date can no longer make old bank evidence fresh. Conversely, an
overdue plan review does not rewrite the source-freshness binary sensor. Review cadence remains
visible through the dedicated schedule/review entities and continues to influence planning
context, not evidence age.

For compatibility, the existing `freshness_mode` attribute remains `age_threshold`. New
attributes expose the effective `freshness_policy`, threshold map, per-source threshold and the
earliest source-evidence `fresh_through` deadline.

## Restore file-based plan no longer removes the schedule

`Configure → Restore file-based plan` now clears only the Home Assistant target-plan override:

- override enabled flag;
- override plan name;
- override budget amount/basis; and
- override instrument/target definitions.

It preserves recurring execution/review scheduling, source configuration, execution policy and
runtime safeguards.

Because an earlier v1.31 reset already removed some existing schedules, v1.33 also adds a
separate **Configure → Execution & review schedule** flow. This allows the schedule to be
restored or changed without creating another Home Assistant target-plan override.

## Live acceptance

1. Upgrade the integration and all three Apps to 1.33.0 in place.
2. Before changing Runtime safeguards, confirm the existing legacy threshold still produces the
   same freshness result as v1.32.0. A previously stale source must remain stale.
3. Confirm normal Comdirect/Trade Republic health, verified HTTPS, source aggregation and
   snapshot integrity remain unchanged.
4. Open **Configure → Execution & review schedule** and verify schedule configuration is
   independent of the target-plan override. If a schedule was previously lost by the v1.31
   reset, restore the intended cadence here.
5. Optionally configure evidence-kind thresholds under **Runtime safeguards**. After saving,
   verify each `source_freshness` row shows the intended effective threshold and the aggregate
   result changes only when every contributing source is inside its own limit.
6. If a Home Assistant target-plan override is enabled in a test installation, use
   **Restore file-based plan** and confirm the execution/review schedule remains configured.
7. Do not run a DKB FinTS probe solely for this release. Registration-propagation research is a
   separate event.

Payload schema 8, REST portfolio schema 1 and Gateway health schema 6 are unchanged. No trading,
order placement, automatic sell, transfer, payment or transaction-history capability is added.
