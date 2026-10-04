# Upgrade to v1.66.0

Update the integration and all four aligned Gateway Apps. No dashboard replacement or Home Assistant config migration is required. DKB starts in its existing CSV authority. The selected account and existing research shadows survive an in-place update, but **the old v1.65.9 shadows cannot be promoted** because they lack authority-grade account provenance.

In DKB admin Ingress, first confirm **Acquisition source: csv** and that holdings and cash both show CSV as authoritative. A new combined **Refresh portfolio now** read, with the existing selected account and normal DKB approvals, stages authority-grade evidence. Review the five-minute detail if useful. Account discovery and the manual read alone do not change planning.

Only after the complete read, inspect the **Acquisition authority** cards, then choose **Manual DKB FinTS** under **Acquisition source** and check the explicit confirmation box. Verify that both capabilities show `fints`, fallback `none`, and independent observation times. Check the PA dashboard plan and authorized investment cash. The booked balance can include pending items and need not equal the DKB app's spendable balance.

Both FinTS observations expire after 14 days from their respective read times, even if the Gateway restarts. At expiry the FinTS snapshot is unavailable and planning blocks for that source; CSV does not take over. Perform another complete manual read to renew the evidence, or deliberately switch to current CSV. The 24-hour shadow status may say `old_observation` while FinTS remains authoritative within its independent 14-day window; the authority cards and PA freshness view are the production indicators.

To roll back to v1.65.9, first switch DKB authority to CSV and confirm CSV publication. A restored backup excludes the new private FinTS evidence and canonical cache; reselect the account if its backup-excluded binding is absent, then perform a new manual read before using FinTS again. No credentials or raw bank responses are stored.
