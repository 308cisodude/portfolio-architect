# Portfolio Architect v1.65.4 upgrade and acceptance

Update the integration and all four version-aligned Gateway Apps. Confirm the integration and engine versions are 1.65.4 and the DKB App reports 1.65.4. No dashboard replacement is required for this release.

In the DKB Gateway App, make a manual read-only booked-balance observation and complete any app approval. This seeds an App-memory system ID only if DKB supplies a bounded ID. Without restarting the App, make a second observation for the same banking user and Girokonto. Verify that the trial line says `prior ID reused: yes` and records whether bank approval was requested. If it says `no`, DKB did not provide an ID accepted by the bounded trial; do not infer that DKB lacks a system ID. An approval on the second read establishes that ID reuse did not remove approval in this trial.

Confirm the private shadow and five-minute side-by-side review still work, and PA remains on DKB CSV cash/holdings. Restart the App: the trial line should disappear, while the bounded cash shadow remains. Do not post banking credentials, account identifiers or balances in a public issue or PR.
