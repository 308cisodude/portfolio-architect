# v1.61.0 validation

The release-preparation contract for v1.61.0 requires the exact published/live-accepted v1.60.0 tracked-source baseline and verifies the Configure removal-confirmation UX without changing runtime architecture.

Required gates include:

- all integration/Gateway/App package versions aligned to v1.61.0;
- executable regression coverage for all four two-step selected-object removal flows;
- complete bilingual English/German removal selection + confirmation copy and immutable context placeholders;
- the primary REST source remains non-removable;
- complete regression suite;
- Python compilation and JSON/YAML parsing;
- `git diff --check`;
- strict publication readiness and repository/history privacy;
- provider-source synchronization idempotence;
- OpenSSL runtime floor positive/negative evidence;
- three independent byte-identical release builds;
- release verification and artifact privacy for every build;
- exact source-release correspondence;
- independent Git-overlay and binary-patch replay from v1.60.0;
- deterministic complete handoff packaging.

Protected GitHub workflows remain authoritative for actual Docker/Supervisor/private-PKI runtime smoke, resolved image OpenSSL evidence and workflow-pinned full-history Gitleaks execution when those facilities are unavailable locally.
