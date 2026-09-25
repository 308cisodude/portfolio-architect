# Portfolio Architect v1.65.1 upgrade and live acceptance

Update the integration and four version-aligned Gateway Apps. Confirm `integration_version`, `engine_version` and App versions show `1.65.1`. An integration reload is enough when both version diagnostics advance; restart Home Assistant only if the update has not loaded.

In DKB Gateway, start one manual read-only holdings refresh with your banking Anmeldename and password. Approve in the DKB app and use the Check button if prompted. On successful complete projection, the screen should show a fresh stored shadow with position count and observation time. After five minutes the detailed rows should disappear; the bounded stored status remains. Restart the DKB Gateway App and check that the status remains fresh. After 24 hours it must show stale until another manual refresh. A failed refresh leaves the last good shadow and its original timestamp intact. Do not share the private position details or registration number in a public issue.

DKB CSV remains the planner's sole holdings and cash input. The next steps are independent FinTS cash research and explicit source-selection design, after live acceptance of this shadow lifecycle.
