# Portfolio Architect 1.56.1

Portfolio Architect v1.56.1 is a narrow Comdirect App-identity migration lifecycle hotfix prepared from the exact published v1.56.0 source baseline. It does not change provider acquisition, REST portfolio schema 1, Gateway health schema 8 (payload schema 8), `fallback_policy: none`, freshness policy, private-PKI trust anchors, planner economics, dashboard entities, or the advisory-only boundary.

## Fixed: canonical Comdirect restart after fresh PhotoTAN bootstrap

The v1.55 migration correctly excluded `comdirect-session.json` from the historical-to-canonical App transfer. The canonical startup validator also required that file to be absent before cut-over. After cut-over, however, a required fresh PhotoTAN bootstrap legitimately creates a new canonical OAuth session. The validator was re-running the pre-cut-over absence rule on every later App startup, so the first restart after a successful fresh bootstrap could falsely classify the canonical session as transferred legacy state and terminate the App with:

`Migrated Comdirect OAuth session must not be present before cut-over`

v1.56.1 keeps the fail-closed boundary and makes the lifecycle distinction explicit:

- migration export/staging/commit still never transfers `comdirect-session.json`;
- the import marker still requires `oauth_session_transferred: false`;
- the first canonical startup after migration still rejects any OAuth session that appears before cut-over;
- the canonical entrypoint still validates committed migration identity **before** renewing the migrated TLS leaf;
- only after the preserved private-PKI leaf has been genuinely renewed and validated for the exact provider-qualified successor hostname may a later canonical restart accept the fresh OAuth session created by the canonical runtime;
- changing only TLS hostname metadata is insufficient because the actual certificate/key pair must validate for the successor hostname under the preserved CA.

The preserved CA fingerprint, exact predecessor/successor hostname relationship, Gateway bearer secret, explicit cut-over marker, imported snapshot identity, Supervisor options reconciliation and all other migration invariants remain enforced.

## v1.56.0 UX/hygiene scope retained unchanged

The deterministic DKB Europe/Berlin + authoritative UTC probe timestamp, Generic Import sensitive-token placement and discovery cleanup, consolidated reference-dashboard incident/LKG presentation, canonical Comdirect naming, Comdirect LEGACY deprecation, and quieter routine Ingress logging remain unchanged.

Historical `portfolio_architect_gateway` remains the final deprecated v1.56.x migration-source line; the active App repository is scheduled to withdraw `portfolio_architect_gateway` in v1.57.0. Canonical `portfolio_architect_gateway_comdirect` remains the production Comdirect identity.

## Compatibility and non-goals

The v1.33.0 source-freshness and plan-schedule separation remains intact: execution timing is anchored to the latest valid Portfolio Architect evaluation, and v1.56.1 does not change any configured freshness threshold.

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 8 current; schemas 1–7 remain supported
- schemas 1–6 remain supported as part of that health-schema compatibility range
- authenticated DKB FinTS acquisition remains disabled
- Trade Republic remains Gateway-owned PDF acquisition; this release does not move PDF parsing into Portfolio Architect
- the historical v1.19.0-rc2 brokerage capability probe is not promoted by this release and no brokerage probe code is included
- presentation schema 2: unchanged
- No dashboard YAML replacement is required for v1.56.1.
- broker schemas 1/2/3: unchanged
- Comdirect explicit `live_api` / complete static `csv` acquisition: unchanged
- Trade Republic PDF acquisition: unchanged
- DKB CSV acquisition: unchanged
- Generic Import mapped CSV acquisition: unchanged
- Authenticated DKB FinTS acquisition remains disabled.
- capability-level acquisition arbitration: not included
- No trading, order, transfer, payment, or transaction-history capability is added.

The affected v1.56.0 installation may update directly to v1.56.1; it should not delete the valid canonical OAuth session, reset private-PKI trust, or reinstall the historical App as part of recovery.
