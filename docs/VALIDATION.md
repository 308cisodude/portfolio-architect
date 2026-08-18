# v1.33.0 validation

Portfolio Architect v1.33.0 is prepared from the exact live-accepted v1.32.0 tracked-source
baseline.

The release must prove:

- integration, engine, common Gateway and all three official App versions align at `1.33.0`;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain unchanged;
- source freshness is evaluated only from bounded source evidence age, never from a plan review
  date;
- an upgrade with no explicit v1.33 evidence-kind settings inherits the previous global
  threshold for every source category, so an existing stale plan cannot become actionable just
  because provider categories were introduced;
- explicit evidence-kind thresholds can differ for live API/Gateway, imported statement,
  imported CSV and other evidence;
- every contributing source must satisfy its own effective threshold for aggregate freshness;
- invalid or materially future source timestamps continue to fail closed;
- the v1.32 per-source evidence/blocker presentation remains bounded and shows each effective
  threshold;
- `Restore file-based plan` clears only target-plan definition options and preserves recurring
  execution/review schedule options;
- a dedicated options flow can configure/disable recurring execution/review scheduling without
  enabling a Home Assistant target-plan override;
- schedule/review entities remain available as planning context but do not authorize stale
  source evidence;
- Comdirect, Trade Republic and DKB provider runtime/diagnostic behavior remains unchanged apart
  from normal package/User-Agent version alignment;
- the v1.31.2 DKB registered anonymous FinTS diagnostic contract remains intact and DKB stays
  non-live; and
- no trading, order placement, automatic sell, transfer, payment or transaction-history
  capability is introduced.

Run the complete regression suite, `git diff --check`, Python compilation, structured-file
parsing, strict publication/privacy checks, three independent reproducible release builds,
release verification, release-artifact privacy validation and independent Git-overlay/binary-
patch replay over the exact v1.32.0 tracked baseline.

Protected GitHub workflows remain authoritative for actual provider-App Docker/private-PKI
smoke execution because Docker is unavailable in the preparation environment.

## Live acceptance

1. Upgrade Portfolio Architect and all three Apps to 1.33.0 in place.
2. Before saving any new freshness policy, prove the v1.32 result is preserved: the old DKB CSV
   remains stale under the existing 168-hour legacy threshold.
3. Confirm Source healthy, Gateway status, verified HTTPS, snapshot integrity and three-provider
   aggregation remain otherwise healthy.
4. Configure the execution/review schedule independently of the target-plan source and confirm
   no plan override is required.
5. Deliberately configure evidence-kind thresholds only after the conservative upgrade result
   is proven. Confirm the aggregate freshness result changes only according to those explicit
   values.
6. If testing target-plan restoration, prove the schedule survives `Restore file-based plan`.
7. Do not reauthenticate Comdirect, re-import Trade Republic, or re-probe DKB solely for this
   release.
