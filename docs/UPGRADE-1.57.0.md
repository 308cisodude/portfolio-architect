# Upgrade to Portfolio Architect v1.57.0

v1.57.0 completes the planned withdrawal of the historical Comdirect Home Assistant App identity. Runtime acquisition, wire schemas, private-PKI trust, freshness, planner behavior and authenticated DKB FinTS remain unchanged from the fully live-accepted v1.56.1 baseline.

## Historical Comdirect App withdrawal

The deprecated `portfolio_architect_gateway` / **Portfolio Architect Gateway — Comdirect LEGACY** package is no longer present in the active App repository and no v1.57.0 Legacy App archive is published.

- Completed installations should run only canonical `portfolio_architect_gateway_comdirect` / **Portfolio Architect Gateway — Comdirect**.
- Do not reinstall or recreate the historical slug.
- Immutable v1.56.x and older tags/releases remain the archival source of the retired package.
- If an installation still has an already-installed supported v1.55/v1.56 Legacy App, do **not** uninstall it before migration. The v1.57.0 canonical Comdirect App deliberately retains the existing bounded migration receiver so that installed Legacy instance can still complete the established explicit same-CA/bearer cut-over.
- Migration still excludes OAuth/session state, requires explicit cut-over, validates predecessor/successor hostname relationship and preserved private-CA identity, and requires fresh provider authentication where the established migration flow calls for it.

## Upgrade sequence

1. Update the Portfolio Architect Home Assistant integration to v1.57.0 and restart Home Assistant when HACS requests it.
2. Update installed active Gateway Apps to v1.57.0: canonical Comdirect, DKB and Trade Republic; update Generic Import only if it is intentionally installed.
3. A completed installation must contain no historical Comdirect LEGACY App. Its absence from the App Store after repository refresh is expected.
4. Verify Portfolio Architect still reports exactly the intended provider source set, verified HTTPS/private-CA trust, fresh/within-policy evidence, inactive Home Assistant LKG and an actionable plan.
5. For an installation that still has an already-installed v1.55/v1.56 Legacy App, complete the documented v1.55 migration to canonical Comdirect before removing the old installation. The fact that the package is no longer offered for new installation does not disable the receiver in canonical v1.57.0.

## Retained Generic Import standalone-smoke isolation

If Generic Import is not part of the real portfolio source set and the retained v1.56 discovery-lifecycle smoke is exercised, do **not** add its discovery card/source to the real Portfolio Architect configuration. Install/start it only as a temporary isolated test, verify its own discovery lifecycle, and remove it again; the standalone smoke must not alter the real canonical provider set. The temporary Generic Import App should be uninstalled after this standalone smoke test.

## Generic Import discovery note

Generic Import still deletes its exact Supervisor discovery record on uninstall. Home Assistant Core may retain an already-created pending Hass.io discovery config-flow card in memory until Home Assistant Core restarts. Do not grant additional Home Assistant API privileges or add a private-frontend workaround solely to remove that transient card.

## Unchanged security and runtime contracts

- REST portfolio schema 1 and Gateway health schema 8 remain unchanged.
- Portfolio payload schema 8 and config-entry schema 12 remain unchanged.
- Provider identities and acquisition modes remain unchanged; `fallback_policy: none` remains mandatory.
- Verified private-PKI HTTPS, bearer authentication and DNS pinning remain unchanged.
- Evidence clocks, freshness policy, source-set atomicity, LKG and anti-rollback behavior remain unchanged.
- Portfolio Architect remains advisory-only and exposes no trading, order, transfer, payment or transaction-history capability.
- DKB authenticated FinTS remains disabled; the anonymous probe remains research-only and cannot replace CSV evidence.
