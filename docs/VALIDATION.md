# v1.56.1 validation

Portfolio Architect v1.56.1 is prepared from the exact published v1.56.0 tracked-source baseline. It is intentionally limited to the canonical Comdirect post-cut-over OAuth-session restart lifecycle plus aligned version/release metadata and executable regression coverage.

Release validation must establish that:

- all integration/common Gateway/all five published App version markers align to 1.56.1 while historical release documentation remains historical;
- Comdirect migration export, staging and commit continue to exclude `comdirect-session.json` and the import marker remains `oauth_session_transferred: false`;
- a session present before the first canonical runtime still fails closed;
- changing only `tls/hostname` cannot bypass that gate: an independent certificate-chain/hostname verifier must validate the actual private-PKI leaf for the exact canonical successor hostname even if the generic leaf-usability helper reports success;
- the canonical entrypoint validates committed migration identity before `prepare_supervisor_tls()` can renew the migrated leaf;
- after that valid successor-bound leaf exists, a fresh canonical OAuth session survives a later App restart;
- preserved CA identity, predecessor/successor hostname binding, explicit cut-over, bearer continuity, acquisition mode, health/wire schemas, freshness/LKG semantics and `fallback_policy: none` remain unchanged;
- all v1.56.0 DKB/Generic Import/dashboard/logging/deprecation contracts remain unchanged;
- authenticated DKB FinTS and capability-level acquisition arbitration remain disabled/deferred;
- `git diff --check`, Python compilation, structured JSON/YAML parsing, the complete regression suite, strict publication/privacy checks, provider-source synchronization, deterministic release builds, release verification, artifact privacy, and exact v1.56.0→v1.56.1 overlay/patch replay pass before handoff.
