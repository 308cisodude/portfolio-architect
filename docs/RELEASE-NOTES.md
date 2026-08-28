# Portfolio Architect 1.55.0

Portfolio Architect v1.55.0 is a narrow structural migration release prepared from the published and fully live-accepted v1.54.0 baseline. It removes the last historical Comdirect App-identity asymmetry by introducing the provider-qualified Home Assistant App slug `portfolio_architect_gateway_comdirect` without silently replacing trust, provider authority or private state.

## Safe Comdirect App-identity migration

The historical `portfolio_architect_gateway` App remains in the release as the explicit migration source. The provider-qualified successor is separately installable and deliberately displayed as **Portfolio Architect Gateway — Comdirect NEW** during coexistence.

Migration is operator-driven and fail-closed. A pristine Comdirect NEW App publishes no Portfolio Architect discovery. It creates an ephemeral TLS migration receiver and one-time code. The historical App accepts no destination URL: it derives only its exact provider-qualified successor hostname, verifies the receiver leaf SHA-256 from the one-time code, and sends a bounded allowlisted state document with per-file SHA-256 integrity metadata.

Long-lived state preserved by migration includes the existing Gateway bearer token, private CA/key and leaf material, Comdirect client credentials, selected investment-account/cash-policy state, acquisition state, staged CSV holdings/cash evidence and canonical snapshot. The Comdirect OAuth/session file is deliberately excluded. This prevents old and new App identities from sharing or racing the same refresh session; a migrated Live API installation performs fresh PhotoTAN bootstrap before discovery.

After import, the historical App is explicitly frozen so provider refresh and OAuth maintenance stop while its already trusted cached HTTPS snapshot remains available to Portfolio Architect. The new App renews only the hostname-specific server leaf from the preserved private CA. It does not publish discovery until health schema 8 is healthy/live with a servable Comdirect snapshot.

Portfolio Architect recognizes only the exact historical-Comdirect → provider-qualified-Comdirect hostname transition. It requires the already trusted CA SHA-256 to remain unchanged, reuses the existing bearer token, requires explicit user confirmation, then validates health schema 8, provider identity, no-fallback state and snapshot timestamp/count/SHA-256 before atomically changing only the primary endpoint and reloading.

## Preserved contracts

- canonical PA provider identity remains `comdirect`; no duplicate provider is introduced;
- Comdirect `live_api` / `csv` arbitration and `fallback_policy: none` are unchanged;
- Trade Republic PDF, DKB CSV and Generic Import CSV acquisition are unchanged; this release does not move PDF parsing into Portfolio Architect;
- evidence-kind freshness, v1.53.1 anti-rollback/static-retention behavior and v1.54 live-LKG semantics are unchanged;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 8 are unchanged; schemas 1–6 remain supported and health schema 7 remains accepted;
- verified private-PKI HTTPS and bearer authentication remain separate trust factors;
- the private CA must be preserved through migration; only the leaf hostname changes;
- Alpine/OpenSSL build policy from v1.54 remains unchanged;
- planner, provider cash, funding topology and advisory execution-path behavior are unchanged;
- authenticated DKB FinTS acquisition remains disabled;
- no trading, order, transfer, payment, sell, withdrawal or transaction-history capability is introduced.


## Compatibility references

The following established release contracts remain unchanged in v1.55.0:

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 8 current; schemas 1–7 remain supported
- presentation schema 2: unchanged
- broker schemas 1/2/3: unchanged
- authenticated DKB FinTS acquisition remains disabled
- Trade Republic statement acquisition does not move PDF parsing into Portfolio Architect
- the v1.19.0-rc2 experimental brokerage probe is not promoted by this release
- the v1.33.0 source-freshness and plan-schedule separation remains intact: recurring scheduling is anchored to the latest valid Portfolio Architect evaluation and this release does not change any configured freshness threshold
- the deprecated dynamic drift implementation remains not included
- No trading, order, transfer, payment, or transaction-history capability is introduced.

No dashboard YAML replacement is required. Follow `docs/UPGRADE-1.55.0.md` exactly and do not uninstall the historical Comdirect App until PA has explicitly accepted and remained healthy on the provider-qualified endpoint.
