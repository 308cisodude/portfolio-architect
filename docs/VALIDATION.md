# v1.62.1 validation

The v1.62.1 release-preparation contract starts from the exact published v1.62.0 source and validates integration-owned first-run setup without weakening the v1.62 Generic graduation or any established provider/security boundary.

Required gates include:

- all integration/Gateway/App package versions aligned to v1.62.1;
- config-entry schema 13 migration that maps every existing entry to `configured` and permits only bounded `source_required`, `plan_required`, `configured` setup states;
- integration initialization that creates only an empty confined PA directory or accepts an already complete valid configuration, while refusing partial/invalid existing state;
- setup-required entries loading without coordinator/entities/Gateway I/O and returning bounded diagnostics;
- Gateway discovery never creating a virgin PA service, including stale v1.62.0 confirmation flows;
- discovered/manual first-source adoption only inside an existing PA entry with verified HTTPS/trust, bearer authentication, exact provider identity and health/snapshot integrity;
- native initial-plan setup using only explicit user choices and source holdings with valid ISIN identity; no financial assumptions or execution provider may be prefilled/invented;
- private staged calculation of all four generated YAML documents before installation, refusal to overwrite existing configuration and reload only after complete validation;
- broker schema 3 allowing zero providers only with zero funding edges;
- preservation of stable v1.62.0 Generic multi-profile behavior, `generic_csv` migration, health schema 10 and discovery schemas 1/2;
- preservation of Comdirect/DKB/TR acquisition, `fallback_policy: none`, REST schema 1, payload schema 8, freshness/LKG/anti-rollback/source-set, planner/funding, private-PKI/bearer/DNS pinning and DKB authenticated-FinTS gates;
- complete regression suite;
- Python compilation and JSON/YAML parsing;
- `git diff --check`;
- strict publication readiness and repository/history privacy;
- provider-source synchronization idempotence;
- OpenSSL minimum-runtime positive/negative evidence;
- three independent byte-identical release builds;
- release verification and artifact privacy for every build;
- exact source-release correspondence; and
- independent Git-overlay and binary-patch replay from v1.62.0.

Protected GitHub workflows remain authoritative for actual Docker/Supervisor/private-PKI execution, resolved OpenSSL image evidence and complete-history Gitleaks validation when Docker is unavailable in the preparation environment.
