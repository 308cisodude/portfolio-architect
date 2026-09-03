# v1.62.3 validation

The v1.62.3 release-preparation contract starts from the exact published v1.62.2 source and validates the Trade Republic German abbreviated month-label compatibility hotfix prompted by the live-observed `Sept.` statement without changing the v1.62 integration-owned first-run architecture or any wire/freshness/planner contract.

Required gates include:

- all integration/Gateway/App package versions aligned to v1.62.3;
- Trade Republic `BARMITTELÜBERSICHT` accepts all 12 canonical German abbreviated month labels (`Jan.`, `Feb.`, `März`, `Apr.`, `Mai`, `Juni`, `Juli`, `Aug.`, `Sept.`, `Okt.`, `Nov.`, `Dez.`);
- all month aliases accepted before v1.62.3 remain supported;
- arbitrary noncanonical/unbounded month spellings remain unsupported;
- missing/unsupported cash as-of evidence is distinguished from true multi-date ambiguity with bounded privacy-safe errors;
- current native Trade Republic cash PDF privately revalidated end-to-end without persisting or committing its raw/private contents;
- Cashkonto arithmetic, custody reconciliation, creation/as-of chronology, cash/holdings independence and atomic rejected-import preservation unchanged;
- v1.62.2 explicit first-run choices and Generic READY-profile colour contract unchanged;
- config-entry schema 13 and stable v1.62.0 Generic multi-profile identity/evidence/discovery behavior unchanged;
- Comdirect/DKB acquisition, `fallback_policy: none`, REST schema 1, payload schema 8, health schema 10, discovery schemas 1/2, freshness/LKG/anti-rollback/source-set, planner/funding, private-PKI/bearer/DNS pinning and authenticated-DKB-FinTS gates preserved;
- complete regression suite;
- Python compilation and JSON/YAML parsing;
- whitespace/diff validation;
- strict publication readiness and repository privacy;
- provider-source synchronization idempotence;
- OpenSSL minimum-runtime positive/negative evidence;
- three independent byte-identical release builds;
- release verification and artifact privacy for every build;
- exact source-release correspondence; and
- independent Git-overlay and binary-patch replay from v1.62.2.

Protected GitHub workflows remain authoritative for actual Docker/Supervisor/private-PKI execution, resolved OpenSSL image evidence and complete-history Gitleaks validation when Docker is unavailable in the preparation environment.
