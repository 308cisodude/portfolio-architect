# Portfolio Architect v1.65.6 — bounded DKB ID diagnostics

The admin-only manual cash research view reports a load result (`missing`, `loaded`, `expired`, `invalid`, or `different_user`), capture result (`valid`, `absent`, or `invalid`), and private save result (`succeeded`, `skipped`, or `failed`). A short HMAC fingerprint allows comparison across App restarts when the private key survives. No raw system ID or unkeyed hash is shown. The 256-bit key is App-private, mode 0600, and excluded from HA backups alongside the bounded system-ID record. These latest-request fields live only in App memory and clear on restart.

v1.65.5's first live restart trial showed `prior ID reused: no` and DKB requested another approval. There was no write-failure warning. The cause is not yet established; these diagnostics are intended to distinguish absent capture, skipped/failed save, invalid/expired state, and binding mismatch. The previously collected cash shadow survived the App restart, while its five-minute detailed review cleared as designed.

DKB CSV stays authoritative for planning. FinTS remains read-only manual research; no credentials or raw bank responses persist. There is no background acquisition or dashboard schema change.
