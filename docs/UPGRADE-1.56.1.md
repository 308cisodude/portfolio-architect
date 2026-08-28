# Upgrade to Portfolio Architect 1.56.1

Version 1.56.1 is a narrow Comdirect migration-lifecycle hotfix from the published v1.56.0 baseline. It fixes the canonical Comdirect App crash loop exposed by the first restart after a completed v1.55/v1.56 App-identity migration and subsequent fresh PhotoTAN bootstrap.

The migration security boundary is preserved: OAuth/session state is still excluded from export, staging and commit; the import marker must still state `oauth_session_transferred: false`; and any OAuth session that appears before the first canonical runtime is still rejected. After the canonical runtime has successfully crossed cut-over and renewed the preserved private-PKI leaf to the exact provider-qualified successor hostname, a fresh canonical OAuth session may legitimately exist and is accepted on later restarts.

No broker configuration migration, source reconfiguration, dashboard replacement, fresh static evidence, or authenticated DKB FinTS change is required.

## Recommended upgrade

1. Update Portfolio Architect through HACS to **1.56.1** and restart Home Assistant once.
2. Update the installed canonical **Portfolio Architect Gateway — Comdirect** App (`portfolio_architect_gateway_comdirect`) to **1.56.1**.
3. Update DKB and Trade Republic to **1.56.1** for release alignment. Update Generic Import only if intentionally installed.
4. Do **not** reinstall historical `portfolio_architect_gateway` on installations where migration is complete. It remains **Comdirect LEGACY / deprecated** during the final v1.56.x migration-source line and is still scheduled for repository withdrawal in v1.57.0.
5. Do not delete the canonical `comdirect-session.json`, regenerate the Gateway bearer token, reset the private CA, or redo PhotoTAN merely because the v1.56.0 crash loop occurred. v1.56.1 is specifically designed to accept the legitimate post-cut-over canonical session already present.

## Live acceptance for an installation affected by the v1.56.0 crash loop

After updating the canonical Comdirect App to v1.56.1:

- the App must start successfully without deleting its existing canonical OAuth session and without requiring a new PhotoTAN bootstrap solely for recovery;
- the preserved private-CA SHA-256 and canonical provider-qualified hostname/endpoint must remain unchanged;
- Portfolio Architect must leave HA LKG after the next successful canonical Comdirect snapshot and return to healthy/live operation with the same three canonical providers;
- Comdirect must remain on its configured acquisition mode (`live_api` in the affected production case), health schema 8, and `fallback_policy: none`;
- no legacy Comdirect discovery or historical App reinstallation is required;
- DKB, Trade Republic, Generic Import, dashboard presentation, freshness thresholds, planner economics, and advisory-only behavior must remain unchanged from v1.56.0.

A second canonical Comdirect App restart after recovery is the critical regression check: the fresh canonical OAuth session must remain accepted and the App must start normally again.

## Security invariant

v1.56.1 does **not** weaken the migration's OAuth exclusion. A session present while the migrated TLS leaf is still bound to the historical hostname is rejected. Merely changing the stored hostname metadata is insufficient: the actual leaf certificate/key must validate for the exact canonical successor hostname under the preserved private CA before post-cut-over session presence is accepted.

Authenticated DKB FinTS remains disabled and capability-level acquisition arbitration remains deferred.

## Retained Generic Import standalone-smoke isolation

If Generic Import is not part of the real portfolio source set and the retained v1.56.0 discovery-lifecycle smoke is exercised, do **not** add its discovery card/source to the real Portfolio Architect configuration. Install/start it only as a temporary isolated test, verify its own discovery lifecycle, and remove it again; the standalone smoke must not alter the real canonical provider set. The temporary Generic Import App should be uninstalled after this standalone smoke test.
