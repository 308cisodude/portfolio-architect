# v1.61.1 validation

The release-preparation contract for v1.61.1 requires the exact published v1.61.0 tracked-source baseline and verifies the provider-neutral Supervisor-discovery lifecycle hotfix without changing Gateway runtime architecture.

Required gates include:

- all integration/Gateway/App package versions aligned to v1.61.1;
- executable regression proving DKB, Trade Republic and Generic Import can each bootstrap the singleton PA entry from verified Supervisor discovery when no entry exists;
- first-run discovery claims `INSTANCE_UNIQUE_ID`, so concurrent provider discoveries collapse to one visible config flow while all provider candidates are retained;
- executable regression proving an existing PA entry aborts unconfigured supplemental top-level discovery rather than showing an Add form;
- candidates deduplicated by immutable `provider_id`, with no Comdirect-specific exclusion when another provider is primary;
- candidate adoption available only below the existing Options flow and still requiring bearer authentication plus verified-HTTPS/provider/health/snapshot-integrity validation;
- all established HTTP→HTTPS, Comdirect-slug migration and trust-refusal paths preserved;
- the v1.61.0 two-step destructive-action confirmation contract preserved;
- complete bilingual English/German discovery-candidate copy;
- complete regression suite;
- Python compilation and JSON/YAML parsing;
- `git diff --check`;
- strict publication readiness and repository/history privacy;
- provider-source synchronization idempotence;
- OpenSSL runtime floor positive/negative evidence;
- three independent byte-identical release builds;
- release verification and artifact privacy for every build;
- exact source-release correspondence;
- independent Git-overlay and binary-patch replay from v1.61.0;
- deterministic complete handoff packaging.

Protected GitHub workflows remain authoritative for actual Docker/Supervisor/private-PKI runtime smoke, resolved image OpenSSL evidence and workflow-pinned full-history Gitleaks execution when those facilities are unavailable locally.
