# v1.55.1 validation

Portfolio Architect v1.55.1 is prepared from the exact published v1.55.0 tracked-source baseline. It changes only Comdirect App-identity migration compatibility/observability plus aligned release metadata; provider identity, wire schemas, acquisition authority, freshness, private-PKI trust, planner economics and the advisory-only boundary remain unchanged.

Validation requires:

- all integration/common Gateway/all five App current-version markers align to 1.55.1 while historical release documentation remains historical;
- the live-observed schema-2 `comdirect-acquisition.json` shape is accepted for migration, while malformed schema-2 history remains fail-closed;
- schema-1 acquisition migration remains compatible;
- `comdirect-session.json` remains excluded;
- migration-code parsing and all legacy-side failures expose only bounded reason classes;
- successor preflight verifies the exact derived hostname, one-time leaf fingerprint and one-time bearer credential before private state transfer;
- an exactly matching already-staged/committed successor can be recovered idempotently without weakening summary validation;
- the historical App no longer turns expected migration failures into a bare HTTP 400 page;
- v1.55 same-CA/bearer preservation, legacy freeze/resume, explicit PA cut-over confirmation, health-schema-8 and snapshot-integrity validation remain unchanged;
- Gateway health schema 8 and REST portfolio schema 1 remain unchanged; schemas 1–7 stay accepted;
- v1.54 OpenSSL >=3.5.8 build policy remains intact across all five Apps;
- authenticated DKB FinTS remains disabled;
- complete regression tests, Python compilation, structured-file parsing, `git diff --check`, strict publication/privacy, provider-source sync, deterministic builds, release verification/artifact privacy and exact v1.55.0→v1.55.1 handoff replay all pass.

Protected GitHub workflows remain authoritative for actual five-App Docker/private-PKI/Supervisor smoke, minimum-OpenSSL enforcement, complete-history/Gitleaks and immutable publication.
