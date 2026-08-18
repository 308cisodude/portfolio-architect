# v1.33.1 validation

Portfolio Architect v1.33.1 is prepared from the exact live-tested v1.33.0
tracked-source baseline.

The release must prove:

- integration, engine, common Gateway and all three official App versions align at `1.33.1`;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain unchanged;
- `plan_review_schedule()` uses the latest valid Portfolio Architect evaluation timestamp and never `oldest_source_generated_at`;
- the exact 18-August live regression produces 7 September 2026 scheduled execution and 5 October 2026 next plan review even while a 31-July DKB CSV remains a valid contributing source;
- v1.33.0 per-source evidence freshness remains source-timestamp based and independent from recurring schedule calculations;
- configured live/statement/CSV/other freshness thresholds are unchanged by the hotfix;
- `Restore file-based plan` continues to preserve recurring execution/review schedule options;
- Comdirect, Trade Republic and DKB provider runtime/diagnostic behavior remains unchanged apart from normal package/User-Agent version alignment;
- the v1.31.2 DKB registered anonymous FinTS diagnostic contract remains intact and DKB stays non-live; and
- no trading, order placement, automatic sell, transfer, payment or transaction-history capability is introduced.

Run the complete regression suite, `git diff --check`, Python compilation,
structured-file parsing, strict publication/privacy checks, three independent
reproducible release builds, release verification, release-artifact privacy
validation and independent Git-overlay/binary-patch replay over the exact v1.33.0
tracked baseline.

Protected GitHub workflows remain authoritative for actual provider-App
Docker/private-PKI smoke execution because Docker is unavailable in the preparation
environment.

## Live acceptance

1. Upgrade Portfolio Architect to 1.33.1 and restart Home Assistant once.
2. Preserve the explicit evidence-kind freshness policy and the restored monthly/day-7/review-lead-2 schedule; do not re-enter them merely for the upgrade.
3. Confirm source freshness remains healthy under the already configured per-kind limits.
4. Confirm **Scheduled execution** changes from the erroneous 7 August 2026 to **7 September 2026**.
5. Confirm **Next plan review** changes from 5 September 2026 to **5 October 2026**.
6. Confirm plan actionability is no longer `overdue_actionable` solely because the old DKB CSV had anchored the schedule backwards.
7. Upgrade all three Gateway Apps in place; preserve App-private state.
8. Do not reauthenticate Comdirect, re-import Trade Republic, or re-probe DKB solely for this release.
