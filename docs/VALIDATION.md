# v1.62.4 validation

The v1.62.4 release-preparation contract starts from the exact published v1.62.3 source and validates two live-observed Home Assistant integration runtime fixes without changing provider acquisition, wire schemas, first-run financial-choice semantics, freshness or planner behavior.

Required gates include:

- all integration/Gateway/App package versions aligned to v1.62.4;
- setup-required entries with `entry.runtime_data is None` unload without attempting forwarded platform teardown;
- normal configured entries with runtime data still unload the established PA platforms;
- `plan_required` → `configured` still requests an immediate config-entry reload after validated atomic configuration installation;
- synchronous CA normalization performs no `ssl.create_default_context` or `load_verify_locations` work;
- semantic private-CA/X.509 validation remains fail-closed in `_rest_ssl_context`;
- both health and snapshot SSL-context constructions remain executor-bound with `hass.async_add_executor_job`;
- v1.62.3 complete bounded German Trade Republic month-label matrix remains unchanged;
- v1.62.2 explicit first-run choices and Generic READY-profile colour contract remain unchanged;
- config-entry schema 13 and stable v1.62.0 Generic multi-profile identity/evidence/discovery behavior unchanged;
- Comdirect/DKB/TR/Generic acquisition, `fallback_policy: none`, REST schema 1, payload schema 8, health schema 10, discovery schemas 1/2, freshness/LKG/anti-rollback/source-set, planner/funding, private-PKI/bearer/DNS pinning and authenticated-DKB-FinTS gates preserved;
- complete regression suite;
- Python compilation and JSON/YAML parsing;
- whitespace/diff validation;
- strict publication readiness and repository privacy;
- provider-source synchronization idempotence;
- OpenSSL minimum-runtime positive/negative evidence;
- three independent byte-identical release builds;
- release verification and artifact privacy for every build;
- exact source-release correspondence; and
- independent Git-overlay and binary-patch replay from v1.62.3.

Protected GitHub workflows remain authoritative for actual Docker/Supervisor/private-PKI execution, resolved OpenSSL image evidence and complete-history Gitleaks validation when Docker is unavailable in the preparation environment.
