# Portfolio Architect v1.57.0

Portfolio Architect v1.57.0 completes the planned historical Comdirect App withdrawal from the exact published/live-accepted v1.56.1 baseline.

- The deprecated historical Home Assistant App `portfolio_architect_gateway` / **Comdirect LEGACY** is removed from the active repository and no v1.57.0 `portfolio-architect-gateway-app` artifact is produced. Immutable v1.56.x and older tags/releases remain the archival source of that retired package.
- Canonical `portfolio_architect_gateway_comdirect` remains **Portfolio Architect Gateway — Comdirect**, stable, and retains the bounded migration receiver so an already-installed supported v1.55/v1.56 Legacy App can still complete the established explicit migration. The historical slug is not reused.
- Build, verification, Docker/OpenSSL workflow, source synchronization, CODEOWNERS, publication checks, privacy allowlists, SBOM and documentation now describe only the four active Apps: Comdirect, DKB, Trade Republic and Generic Import.
- The v1.56.1 post-cut-over Comdirect restart fix remains unchanged: migration still forbids OAuth transfer/pre-cut-over session state and validates the exact successor-bound private-PKI leaf before accepting a later canonical session.
- The v1.56 deterministic DKB Europe/Berlin + UTC timestamp presentation, Generic Import sensitive-token placement and Supervisor discovery cleanup, consolidated reference-dashboard incident/LKG presentation, canonical Comdirect naming, and quieter routine Ingress logging remain unchanged. No dashboard YAML replacement is required for v1.57.0. Home Assistant Core may retain an already-open Hass.io discovery config-flow card until Core restarts even after Supervisor has deleted the discovery; Portfolio Architect adds no elevated-permission workaround.

REST portfolio schema 1, Gateway health schema 8, payload schema 8, config-entry schema 12, provider identities, acquisition modes, `fallback_policy: none`, evidence clocks/freshness, LKG/anti-rollback behavior, planner economics, private-PKI HTTPS, bearer authentication, DNS pinning and source-set atomicity remain unchanged. No trading, order, transfer, payment, or transaction-history capability is added. Authenticated DKB FinTS remains disabled.

## Retained compatibility contracts

The v1.57.0 repository-withdrawal change does not alter the established machine-readable compatibility surface:

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 8 current; schemas 1–7 remain supported
- schemas 1–6 remain supported for the earlier health-negotiation compatibility covered by retained regressions
- presentation schema 2 remains unchanged
- broker schemas 1/2/3 remain supported
- authenticated DKB FinTS acquisition remains disabled
- Trade Republic statement/PDF parsing remains inside the provider Gateway; this release does not move PDF parsing into Portfolio Architect
- The historical experimental `v1.19.0-rc2` brokerage probe is not promoted by this release and its probe module is not included in the stable runtime
- The v1.33.0 source-freshness and plan-schedule separation remains intact: recurring scheduling stays anchored to the latest valid Portfolio Architect evaluation and this release does not change any configured freshness threshold
