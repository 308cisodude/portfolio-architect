# Portfolio Architect v1.65.2 upgrade and live acceptance

Update the integration and all four version-aligned Gateway Apps. Confirm `integration_version` and `engine_version` are `1.65.2` and the Gateway App versions match. An integration reload is sufficient when the diagnostics advance; restart Home Assistant only if it has not loaded the update.

In DKB Gateway, retain the current DKB cash CSV. In **Read-only Girokonto booked-balance research**, enter your banking Anmeldename and password and the final four digits of the intended Girokonto IBAN. Approve the login in the DKB app, then use the Check button if the Gateway asks. The intended result is `retrieved`, with one selected EUR account and a five-minute comparison of CSV Kontostand and FinTS booked balance, each with its own date. Do not treat differences as an automatic error, and do not infer spendable or authorized investment cash from the FinTS amount.

After five minutes, the amount comparison must disappear; the status should retain observation time and bank balance date without amount. Restart the DKB Gateway App to check that the stored observation status survives. After 24 hours it must be labeled old until a new manual refresh. A failed refresh must leave the last successful shadow and original observation time intact. Do not share screenshots with private balances or credentials in a public issue.

DKB CSV is still the only cash and holdings evidence sent to the planner. The presentation-layer problem of making planner blockers immediately obvious remains a separate follow-up.
