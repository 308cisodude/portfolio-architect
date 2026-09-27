# Upgrade to v1.65.6

Update the Portfolio Architect integration and all four version-aligned Gateway Apps. The DKB App retains its cash and holdings shadow files and existing system-ID record across an in-place upgrade. The new App-private HMAC key is created on the first valid system-ID capture or load, mode 0600, and is excluded from cold HA backups. An HA restore cannot restore either private file and will require an approved seed read.

For acceptance, first inspect the admin page after a manual cash read for `capture valid` and `save succeeded`. A restart clears the latest-request diagnostics and five-minute detail. A subsequent manual read for the same banking user reports the load reason and keyed fingerprint. Do not treat `prior ID reused: yes` as proof that the bank accepted the session; record approval separately. Inspect an actual App backup for the exclusion of both private files before relying on the backup boundary. Do not export the files or raw bank responses.

DKB CSV authority, the planner, and reference dashboard are unchanged.
