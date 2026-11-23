# Upgrade to v1.66.4

Update the Portfolio Architect integration and installed Gateway Apps to v1.66.4. Restart Home Assistant when prompted. Keep a copy of your current dashboard YAML, then replace it with the v1.66.4 bilingual or single-language YAML from the release. Existing source settings and observations are preserved.

## Check normal operation

In Runtime health, check that a healthy live calculation still shows **Snapshot freshness**. In the DKB Gateway's **Acquisition authority** section, check that both FinTS observations show **Available for planning** if the complete published snapshot is usable. No early manual read is needed.

## Check the next natural expiry

With FinTS selected, let its usual observation window expire. Before refreshing DKB, check that expired observations are labelled **Expired** while FinTS remains authoritative and automatic fallback shows **none**. If only one clock has expired, the other can be in range but **Not usable for planning** because the complete pair is unavailable.

After PA polls, **Source unavailable** should name DKB. The compact **Retained calculation** tile should show the retained calculation's freshness without naming a provider as stale. Historical provider dates remain in the detailed plan explanation. After the usual manual FinTS refresh and PA's next poll, check that the plan returns to Live if all sources pass and that the configured DKB cash cap remains in effect.
