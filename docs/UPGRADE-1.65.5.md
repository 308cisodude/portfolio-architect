# Portfolio Architect v1.65.5 upgrade and acceptance

Update the integration and four version-aligned Gateway Apps. The DKB App keeps `backup: cold`; no dashboard YAML replacement is needed. The first successful read after upgrading v1.65.4 may require DKB banking-app approval because the old in-memory ID cannot be migrated. Enter banking credentials for each manual request.

1. Make a complete manual DKB booked-balance observation, approving the bank request if asked. This seeds the private ID for at most 72 hours.
2. Restart **only** the DKB Gateway App. Repeat the manual read with the same user. Check that `prior ID reused: yes` and record whether the bank requested approval. Do not share credentials or the identifier.
3. Verify a normal cold HA backup stops and restarts the App, then confirm that the next manual read within 72 hours can reuse the ID. Inspect the actual DKB App backup archive: `dkb-fints-system-id.json` and any `.*system-id.json.*` temporary file must be absent. Do not publish the archive or the private state file.
4. Test an idle interval exceeding 25 hours with no cash research requests between seed and probe. Record both trial booleans. A bank challenge may still occur; the code does not override DKB authentication decisions.

The 72-hour retention starts with the approved successful read and does not slide on approval-free reads. After expiry or product reconfiguration, a fresh bank approval may be needed. DKB CSV remains authoritative; the planner must not change when the FinTS cash shadow is refreshed.
