# Portfolio Architect 1.33.0

Version 1.33.0 is the **source-freshness and plan-schedule separation** release prepared from
the exact live-accepted v1.32.0 tracked-source baseline.

The release follows two live observations: v1.32 finally exposed that a DKB CSV source was the
freshness blocker, and comparison with the earlier v1.30 dashboard proved that the same old CSV
had previously remained "fresh" only because a configured review date replaced the source-age
gate. The v1.31 `Restore file-based plan` operation had also removed that schedule together
with the target-plan override.

## Evidence freshness is no longer review cadence

Provider evidence age and recurring review dates are now separate controls.

`is_data_fresh()` evaluates every contributing source against its effective evidence-age
threshold. It no longer asks whether `next_review_on` lies in the future. Therefore:

- a future review date cannot authorize old provider evidence;
- an overdue plan review does not rewrite source freshness;
- one stale contributing source still makes the aggregate plan non-actionable; and
- invalid/materially future source timestamps remain fail-closed.

The existing `freshness_mode: age_threshold` token is retained for machine-state compatibility.
New diagnostics expose an explicit freshness-policy token, the effective threshold map and the
earliest evidence-age `fresh_through` deadline.

## User-owned evidence-kind thresholds

v1.33 can apply separate bounded thresholds to:

- `live_api` and provider `gateway_snapshot` evidence;
- `imported_statement` evidence;
- `imported_csv` evidence; and
- `other` evidence.

Live/other limits are bounded to 1–168 hours. Imported statement/CSV limits are bounded to
1–744 hours (31 days).

Migration is intentionally conservative. Existing installations do not receive a longer
provider-specific lifetime automatically. When none of the new options has been saved, every
category inherits the pre-v1.33 global `freshness_hours` value. A stale v1.32 plan therefore
stays stale immediately after upgrading to v1.33.

Only an explicit operator save under **Runtime safeguards** activates different evidence-kind
values.

## File-plan restoration no longer destroys scheduling

The reset boundary is corrected. **Restore file-based plan** now removes only the Home
Assistant target-plan definition override. It preserves:

- recurring schedule enabled/disabled state;
- plan frequency used by the schedule;
- execution days/month/quarter offset;
- review lead time;
- provider/source configuration;
- execution/cost policy; and
- runtime safeguards.

A dedicated **Execution & review schedule** options flow is added so a schedule can be restored
or changed while the target architecture continues to come from `portfolio.yaml`. This is
particularly useful for installations whose schedule was already lost during the v1.31 plan
migration.

## v1.32 observability remains the presentation layer

The existing v1.32 per-source `source_freshness` rows and native dashboard blocker summary are
reused. Each row now carries the source's effective evidence-kind threshold, so the dashboard
can naturally render, for example, a DKB CSV blocker against a 31-day policy without new custom
frontend code.

The bilingual reference dashboard itself is unchanged from v1.32.0.

## Provider runtimes preserved

Comdirect acquisition/OAuth/session/PhotoTAN/cash behavior is unchanged. Trade Republic
statement import/private diagnostic behavior is unchanged, and this release does not move PDF parsing into Portfolio Architect. DKB keeps the live-accepted v1.31.2
registered anonymous FinTS diagnostic contract and remains experimental/manual-only/non-live.
The current `9078` registration-propagation evidence is not re-probed by this release. DKB live Gateway acquisition remains a later authenticated milestone after the bank-level and authenticated user-capability gates.

## Preserved contracts

- portfolio payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged; schemas 1–5 remain supported where previously supported;
- multi-source atomicity and no-partial-live-aggregate behavior: unchanged;
- one stale source remains sufficient to make a recommendation non-actionable;
- v1.31 canonical accumulating Robotics target and outside-scope distributing holding: unchanged;
- provider-aware execution policy/broker schema 2: unchanged;
- private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and
  no-plaintext fallback: unchanged;
- provider diagnostic evidence policy from v1.32: unchanged; and
- the historical `v1.19.0-rc2` brokerage probe remains excluded and is not promoted by this release; and
- advisory/no-trading boundary: unchanged.

No trading, order, transfer, payment, or transaction-history capability is added. No automatic sell capability is added.

See `docs/UPGRADE-1.33.0.md` for the conservative migration and live-acceptance sequence.
