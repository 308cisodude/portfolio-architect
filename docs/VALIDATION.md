# v1.61.2 validation

The release-preparation contract for v1.61.2 requires the exact published v1.61.1 tracked-source baseline and verifies only the live-observed Primary REST Gateway identity-context correction while preserving the v1.61.1 provider-neutral discovery lifecycle and all Gateway/provider runtime contracts.

Required gates include:

- all integration/Gateway/App package versions aligned to v1.61.2;
- executable regression proving a runtime-validated primary provider identity remains visible when the form's one-off fresh health lookup raises a bounded `PortfolioRestError`;
- executable regression proving a changed primary endpoint still fails closed when the current primary identity cannot be freshly established, even when runtime display identity and candidate health both indicate the expected provider;
- display fallback and save-time verification kept as separate variables/decision paths;
- v1.61.1 fresh-install provider-neutral bootstrap, concurrent singleton-flow collapse, existing-entry discovery suppression and provider-keyed candidate adoption preserved;
- v1.61.0 two-step destructive-action confirmation preserved;
- all established HTTP→HTTPS, Comdirect-slug migration and trust-refusal paths preserved;
- complete regression suite;
- Python compilation and JSON/YAML parsing;
- `git diff --check`;
- strict publication readiness and repository/history privacy;
- provider-source synchronization idempotence;
- OpenSSL runtime floor positive/negative evidence;
- three independent byte-identical release builds;
- release verification and artifact privacy for every build;
- exact source-release correspondence;
- independent Git-overlay and binary-patch replay from v1.61.1;
- deterministic complete handoff packaging.

Protected GitHub workflows remain authoritative for actual Docker/Supervisor/private-PKI runtime smoke, resolved image OpenSSL evidence and workflow-pinned full-history Gitleaks execution when those facilities are unavailable locally.
