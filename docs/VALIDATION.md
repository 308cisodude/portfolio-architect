# v1.53.1 validation

Portfolio Architect v1.53.1 is prepared from the exact published v1.53.0 tracked-source baseline. It is a narrow correctness hotfix for live-acceptance findings; the v1.53 provider-neutral acquisition control plane remains the architectural baseline.

Release validation requires:

- all integration/common Gateway/all four App current-version markers align to 1.53.1 while historical release documentation remains historical;
- Gateway health schema 8 and REST portfolio schema 1 remain unchanged; schemas 1–7 stay accepted;
- a snapshot timestamp may move backwards only when validated schema-8 history proves an explicit `operator` switch from the last accepted acquisition method to the current active method after the previously accepted snapshot was generated; same-method and unproven rollback remain fail-closed;
- the same transition rule applies to primary and supplemental Gateway snapshots;
- PA-local primary integrity rejection while HA LKG is active produces a bounded primary Gateway unavailable-source identity instead of an empty set/`None`; Gateway-local non-live attribution from v1.26.6 remains independently valid;
- active `csv` and `pdf` Gateway methods use effective unbounded snapshot serving (`max_cached_snapshot_age_seconds=0`) while retaining the original evidence timestamp; non-static/live methods continue to honor the configured bounded cache age;
- Comdirect CSV, DKB CSV, Trade Republic PDF and Generic Import CSV all follow that static-serving rule;
- supplemental health `snapshot_available=false` and REST HTTP 503 map to `snapshot_unavailable`, do not populate the integrity-error repair path, and still preserve atomic all-configured-source LKG behavior;
- true supplemental provider identity, timestamp, position-count and fingerprint inconsistencies still classify as integrity failures;
- v1.53 explicit activation, crash-safe pending-state recovery, failed-live-read rollback and `fallback_policy: none` remain unchanged;
- DKB FinTS remains research-only/non-activatable and no authenticated probe or acquisition is introduced;
- configured freshness values, independent evidence clocks, planner economics, provider cash/funding/execution semantics, private-PKI/DNS pinning and the advisory-only boundary remain unchanged;
- complete regression tests, Python compilation, JSON/YAML parsing and `git diff --check` pass;
- strict publication/privacy, provider-source synchronization, deterministic release builds, source-release verification, release-artifact privacy and independent Git-overlay/binary-patch replay all pass.

Protected GitHub workflows remain authoritative for complete-history/Gitleaks and actual provider-App Docker/private-PKI smoke execution when unavailable locally.
