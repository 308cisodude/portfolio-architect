# v1.57.0 validation

Portfolio Architect v1.57.0 is prepared from the exact published/live-accepted v1.56.1 tracked-source baseline. It is intentionally limited to withdrawing the historical Comdirect App from the active repository/publication surface while retaining canonical migration-receiver compatibility.

Release validation must establish that:

- integration/common Gateway and all four active App version markers align to 1.57.0 while historical release documentation remains historical;
- `home_assistant_app/portfolio_architect_gateway/` is absent from the active source tree and no v1.57.0 historical Comdirect App archive is built, verified, uploaded, Docker-built, smoke-tested, source-synchronized, CODEOWNERS-protected, or listed in the active SBOM;
- canonical `portfolio_architect_gateway_comdirect` remains stable and retains the exact predecessor/successor hostname mapping, migration schema 1 receiver, same-CA/bearer preservation, `oauth_session_transferred: false`, explicit cut-over and post-cut-over restart hardening from v1.56.1;
- already-installed supported v1.55/v1.56 Legacy instances can still hand their bounded payload to the v1.57.0 canonical receiver; the historical slug is not reused;
- canonical Comdirect, DKB, Trade Republic and Generic Import remain the only active App packages; DKB/Trade Republic maturity and Generic Import experimental status are unchanged;
- the v1.56 UX/hygiene behavior and the v1.56.1 Comdirect lifecycle fix remain unchanged;
- authenticated DKB FinTS and capability-level acquisition arbitration remain disabled/deferred;
- REST portfolio schema 1, Gateway health schema 8, payload schema 8, config-entry schema 12, `fallback_policy: none`, freshness/LKG/anti-rollback semantics, planner economics, verified private-PKI transport and the advisory-only boundary remain unchanged;
- `git diff --check`, Python compilation, JSON/YAML parsing, the complete regression suite, strict publication/privacy checks, provider-source synchronization, deterministic release builds, release verification, artifact privacy, and exact v1.56.1→v1.57.0 overlay/patch replay pass before handoff.
