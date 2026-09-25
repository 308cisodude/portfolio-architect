# Portfolio Architect v1.65.1 — durable manual DKB holdings shadow

The live v1.65.0 acceptance confirmed that complete normalized DKB FinTS holdings can be projected and that detailed admin review expires after five minutes. This release saves only complete bounded ISIN, quantity, total value, total currency and observation time to an App-private file after a successful manual request. The shadow survives an App restart and is marked stale after 24 hours. Failed or incomplete refreshes retain the previous observation, which still ages normally. Changing the FinTS product registration clears it.

The DKB admin screen and bounded status report whether the shadow is absent, fresh, stale or invalid, with observation time and position count. Status and Home Assistant receive no position rows. The full comparison view remains transient for five minutes. Credentials, account numbers, raw bank instrument text and responses are never saved. The existing bank approval flow remains manual and read-only.

This is still research evidence. DKB CSV holdings and cash remain authoritative for planning. There is no background polling, planner source switch, automatic CSV comparison or FinTS cash acquisition. An invalid stored shadow is unusable; a failed refresh never makes an old shadow fresh.
