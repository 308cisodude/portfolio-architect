# Portfolio Architect v1.65.5 — restart-safe DKB system-ID trial

The read-only DKB cash research trial now retains one bounded bank-assigned FinTS system ID in App-private storage. This allows a later **manual** observation for the same banking user to test reuse after the daily cold backup restarts the App. A successful approved read starts a fixed 72-hour window. Approval-free reads do not extend it. An expired, corrupt, or differently bound record is not reused.

The file has mode `0600` and is excluded from Home Assistant App backups. An HA restore therefore needs a new approved seed observation. The identifier is not shown, logged, included in diagnostics, or sent to Portfolio Architect. Credentials, raw responses, and dialog state remain transient. The administrator still enters the banking login and password for each manual request.

DKB CSV remains the sole holdings and cash authority for planning. No background acquisition, source switch, or dashboard change is included. The 24-hour cash observation shadow and five-minute detailed review remain separate from the 72-hour system-ID research window.
