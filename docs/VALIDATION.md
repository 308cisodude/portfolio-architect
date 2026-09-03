# v1.62.2 validation

The v1.62.2 release-preparation contract starts from the exact published v1.62.1 source and validates explicit first-run choices plus the Generic READY-profile colour correction without changing the v1.62.1 integration-owned architecture.

Required gates include:

- all integration/Gateway/App package versions aligned to v1.62.2;
- config-entry schema 13 and `source_required` / `plan_required` / `configured` lifecycle unchanged;
- every **Complete initial setup** field rendered without a schema default that Home Assistant can turn into an implicit investment choice;
- target instruments initially unselected and first-run numeric controls initially blank;
- instrument/policy/normalization booleans represented as explicit unanswered Yes/No choices rather than unchecked Boolean selectors;
- backend field-level rejection of omitted/blank first-run choices before configuration generation;
- staged engine validation and atomic four-file installation preserved;
- Generic profile SETUP REQUIRED amber / READY blue presentation while active/authoritative CSV remains green;
- stable v1.62.0 Generic multi-profile identity/evidence/discovery behavior unchanged;
- Comdirect/DKB/TR acquisition, `fallback_policy: none`, REST schema 1, payload schema 8, health schema 10, freshness/LKG/anti-rollback/source-set, planner/funding, private-PKI/bearer/DNS pinning and authenticated-DKB-FinTS gates preserved;
- complete regression suite;
- Python compilation and JSON/YAML parsing;
- `git diff --check` equivalent whitespace validation;
- strict publication readiness and repository privacy;
- provider-source synchronization idempotence;
- OpenSSL minimum-runtime positive/negative evidence;
- three independent byte-identical release builds;
- release verification and artifact privacy for every build;
- exact source-release correspondence; and
- independent Git-overlay and binary-patch replay from v1.62.1.

Protected GitHub workflows remain authoritative for actual Docker/Supervisor/private-PKI execution, resolved OpenSSL image evidence and complete-history Gitleaks validation when Docker is unavailable in the preparation environment.
