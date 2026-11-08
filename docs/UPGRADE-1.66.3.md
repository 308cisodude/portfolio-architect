# Upgrade to v1.66.3

Update Portfolio Architect and all four version-aligned Gateway Apps using the normal release workflow. Restart Home Assistant when Marketplace requests it. No dashboard replacement or configuration migration is required for this release. Preserve the current DKB observation for the planned November 15 expiry trial; this release needs no DKB read.

In the TR App, verify one upload form and separate holdings/cash statuses. Upload the new combined net worth PDF once. Confirm six Brokerage positions and the Cashkonto balance against the private statement; crypto must not appear as a security or investment cash. Both evidence dates should be the statement day at 00:00 Europe/Berlin, not the security price dates or upload time. Confirm the last complete PA calculation refreshes and independent source dates remain understandable.

For first live cash acceptance, compare the Cashkonto result with the separate cash account statement as of the same date (or reconcile known intervening booked movements). Do not assume it is a live spendable balance or subtract pending transactions without evidence. The combined statement reports account cash; the standalone account statement retains its transaction/custody reconciliation path.

Check the Marketplace banner, condensed overview and links after updating PA. The two pending DKB review/retained-calculation checks remain pending until their planned live observations. To reproduce the cross-source retained-calculation case fully, let DKB expire first, then import newer TR evidence before refreshing DKB; a TR import made while DKB is still fresh can already be part of the last complete calculation.

On rejection, both prior snapshots remain unchanged. Keep the old PDF families available. Before downgrading, restore a backup: older importers give the legacy cash sidecar precedence, so a downgrade without restoring aligned state could resurrect old cash evidence.
