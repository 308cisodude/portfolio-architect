# Upgrade to v1.65.8

Update the integration and all four version-aligned Gateway Apps. No dashboard YAML replacement is required. The App-private DKB shadow survives an in-place update; the system-ID file and HMAC key remain excluded from Home Assistant backups. No credentials or raw bank response are retained.

For live acceptance, take one step at a time. First, perform one manual DKB cash read and approve in the banking app only if requested. Inspect the admin research diagnostics: `capture valid`, `save succeeded`, and a keyed fingerprint indicate that an ID was stored. If those are absent, stop and report only the bounded diagnostic categories. Do not share the ID or balance.

Only after a successful save, restart the DKB Gateway App manually and make one more manual cash read with the same banking user and account suffix. Compare `prior ID reused`, approval requested, load result, and fingerprint. An approval-free result demonstrates reuse for this trial; it does not establish a 25-hour lifetime. Do not perform the 25-hour trial until this restart acceptance succeeds. CSV planning remains unchanged.
