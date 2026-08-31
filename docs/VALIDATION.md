# v1.62.0 validation

The release-preparation contract for v1.62.0 requires the exact published/live-accepted v1.61.2 tracked-source baseline and validates Generic Import graduation without weakening provider isolation, transport trust or native-provider acquisition.

Required gates include:

- all integration/Gateway/App package versions aligned to v1.62.0;
- Generic Import App `stage: stable` with no Home Assistant/Auth/Docker API privileges;
- bounded multi-profile registry with immutable generated provider identities and backward-compatible `generic_csv` migration;
- independent per-profile mapping, holdings snapshot, optional investment cash and evidence clocks;
- rejected import retention of the prior canonical snapshot and transient raw CSV handling;
- restart-safe normalized profile state and explicit profile-scoped deletion;
- Supervisor discovery only for ready profiles, with exact schema-2 provider path/name validation and schema-1 compatibility;
- Gateway health schema 10 `provider_name` with schemas 1–9 retained;
- Generic-only provider-neutral first-run bootstrap and existing-entry candidate behavior;
- maximum eight supplemental REST sources without changing the singleton config-entry architecture;
- preservation of Comdirect/DKB/TR acquisition, `fallback_policy: none`, REST schema 1, payload schema 8, config-entry schema 12, freshness/LKG/anti-rollback/source-set, planner/funding, private-PKI/bearer/DNS pinning and DKB authenticated-FinTS gates;
- complete regression suite;
- Python compilation and JSON/YAML parsing;
- `git diff --check`;
- strict publication readiness and repository/history privacy;
- provider-source synchronization idempotence;
- OpenSSL minimum-runtime positive/negative evidence;
- three independent byte-identical release builds;
- release verification and artifact privacy for every build;
- exact source-release correspondence; and
- independent Git-overlay and binary-patch replay from v1.61.2.

Protected GitHub workflows remain authoritative for actual Docker/Supervisor/private-PKI execution, resolved OpenSSL image evidence and complete-history Gitleaks validation when Docker is unavailable in the preparation environment.
