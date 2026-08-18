# v1.32.0 validation

Portfolio Architect v1.32.0 is a provider freshness-observability and provider-diagnostics
foundation release based on the exact immutable v1.31.2 tracked source baseline.

The release must prove:

- integration, engine, common Gateway and all three official App versions align at `1.32.0`;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain unchanged;
- the established oldest-contributing-source freshness gate remains authoritative;
- the configured freshness threshold is not relaxed or replaced by provider-specific policy;
- per-source freshness evidence identifies source/provider, evidence kind, timestamp, age,
  applicable threshold and whether the source is within that threshold;
- the exact live three-source regression (Comdirect + Trade Republic + DKB CSV) identifies
  only the old DKB CSV source as stale under the 168-hour policy;
- invalid or materially future source timestamps fail observability closed;
- native English/German dashboard Tiles surface the stale-source/actionability detail without
  custom frontend dependencies;
- Trade Republic persists at most the latest bounded allowlisted import diagnostic in
  App-private mode `0600`, never the uploaded PDF or a PDF fingerprint;
- injected private text cannot escape through Trade Republic persisted diagnostics or Web UI,
  including after a malformed/tampered diagnostic state file is reopened;
- a later successful Trade Republic import replaces obsolete failure evidence;
- Comdirect keeps bounded error/re-auth classifications, App-relative Ingress navigation and
  no authenticated raw/free-text response persistence;
- DKB retains the live-accepted v1.31.2 exact-25-character HKVVB registration, Ingress-safe
  navigation and bounded anonymous FinTS diagnostics without enabling live acquisition;
- the common provider diagnostic policy explicitly requires classified evidence, bounded
  persistence/redaction and no raw-upstream-body retention; and
- no trading, order placement, automatic sell, transfer, payment or transaction-history
  capability is introduced.

Run the complete regression suite, `git diff --check`, Python compilation, structured-file
parsing, strict publication/privacy checks, three independent reproducible release builds,
release verification, release-artifact privacy validation and independent Git-overlay/binary-
patch replay over the exact v1.31.2 baseline.

Protected GitHub workflows remain authoritative for actual provider-App Docker/private-PKI
smoke execution because Docker is unavailable in the preparation environment.

## Live acceptance

1. Upgrade the Home Assistant integration to 1.32.0 and restart once.
2. Replace the reference bilingual dashboard YAML if the new blocker detail should be visible.
3. Upgrade Comdirect, DKB and Trade Republic Apps in place; preserve each App-private volume.
4. Do not reauthenticate Comdirect when the existing session is healthy.
5. Do not re-import the Trade Republic statement merely because of the package upgrade.
6. Do not re-enter the DKB FinTS registration or run another DKB probe merely for v1.32.0.
7. Confirm the current stale-source topology remains fail closed: Snapshot freshness stays
   off and the plan remains non-actionable while the old DKB CSV source exceeds the existing
   168-hour threshold.
8. Confirm the new attributes/dashboard identify DKB CSV as the actual freshness blocker and
   do not falsely blame the newer Comdirect or Trade Republic sources.
9. Confirm Source healthy, Gateway status, verified HTTPS, snapshot integrity and provider
   aggregation remain otherwise unchanged.

The later DKB propagation retry remains a separate research event. If a future probe yields
BPD with `HIWPDS`, authenticated user capability/UPD and decoupled-authentication research is
still required before any holdings implementation.
