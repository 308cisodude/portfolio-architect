# Upgrade to v1.65.9

Update the integration and all four aligned Gateway Apps. No dashboard replacement or Home Assistant config migration is needed. Existing DKB CSV imports and App-private research shadows survive an in-place update. CSV stays authoritative.

In DKB admin Ingress, confirm **DKB CSV · authoritative**. Save an investment cash policy only if you intend to change the planner's authorization from the existing CSV cash balance; a cap or reserve takes effect immediately. v1.65.8 ignores that policy if rolled back, so review or pause DKB planning before such a rollback.

Discover the eligible EUR accounts with the DKB banking login name and banking password. Complete the banking-app challenge if requested. Choose the one relevant account from the masked, five-minute selector. The saved page label contains four trailing digits; the underlying private binding checks the complete bank account identity. Restoring an HA backup requires selection again.

Use **Refresh portfolio now** with the same banking login name and password. Complete each banking-app challenge in turn. Review the one-depot and booked-balance observations within five minutes, and the dated shadow status. Differences in value or timestamp from CSV are expected, with no automatic match judgment. The planner still uses CSV. Report only bounded status categories if a read fails, never credentials or raw bank data.
