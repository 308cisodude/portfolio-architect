# Portfolio Architect 1.33.1

Version 1.33.1 is a narrow **plan-schedule anchor hotfix** prepared from the exact
live-tested v1.33.0 tracked-source baseline.

Live acceptance of v1.33.0 proved that source freshness and review cadence are now
correctly independent, but exposed one remaining legacy dependency: recurring
execution/review dates were still anchored to `oldest_source_generated_at` before
falling back to the portfolio evaluation timestamp. With a valid 31-day DKB CSV
from 31 July and a current evaluation on 18 August, that produced an obsolete
**7 August** scheduled execution and **5 September** next plan review.

## Schedule dates use the latest valid evaluation

`plan_review_schedule()` now derives its cycle only from Portfolio Architect's
existing latest valid evaluation timestamp (`data_timestamp`). It no longer uses
the oldest contributing source timestamp as a schedule anchor.

The exact live topology is regression-covered:

- latest valid Portfolio Architect evaluation: 18 August 2026;
- recurring frequency: monthly;
- execution day: 7;
- review lead: 2 days;
- DKB CSV evidence: 31 July 2026, still valid under the explicitly configured
  744-hour CSV freshness policy;
- expected scheduled execution: **7 September 2026**; and
- expected next plan review: **5 October 2026**.

The old DKB CSV timestamp remains relevant only to its own evidence-age freshness
check. It cannot move the recurring plan calendar backwards.

## v1.33.0 source-freshness and plan-schedule separation preserved

This hotfix does not change any configured freshness threshold, evidence-kind
classification, stale-source fail-closed behavior, runtime safeguards, target-plan
configuration, or execution/review schedule settings.

The explicit 24h/168h/744h/24h live acceptance profile remains operator-owned
configuration; no longer-lived document policy becomes a product default.

`Restore file-based plan` retains the v1.33.0 corrected boundary and continues to
preserve schedule/runtime/source options while clearing only Home Assistant target-
plan override fields.

## Provider runtimes preserved

Comdirect acquisition/OAuth/session/PhotoTAN/cash behavior is unchanged. Trade
Republic statement import/private diagnostic behavior is unchanged; this release does not move PDF parsing into Portfolio Architect. DKB retains the
live-accepted registered anonymous FinTS diagnostic contract and remains
experimental/manual-only/non-live; no new DKB probe is required for this release.
DKB live Gateway acquisition remains a later authenticated provider-specific milestone.

## Preserved contracts

- portfolio payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged; schemas 1–5 remain supported where previously supported;
- v1.33.0 per-source/evidence-kind freshness policy: unchanged;
- source evidence timestamps remain authoritative for source freshness only;
- target-plan and recurring-schedule persistence boundaries: unchanged from v1.33.0;
- v1.31 canonical accumulating Robotics target and outside-scope distributing holding: unchanged;
- provider-aware execution policy/broker schema 2: unchanged;
- private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-plaintext fallback: unchanged;
- provider diagnostic evidence policy from v1.32: unchanged;
- historical `v1.19.0-rc2` brokerage probe remains excluded and is not promoted by this release; and
- advisory/no-trading boundary: unchanged.

No trading, order, transfer, payment, or transaction-history capability is added.
No automatic sell capability is added.

See `docs/UPGRADE-1.33.1.md` for the live-acceptance sequence.
