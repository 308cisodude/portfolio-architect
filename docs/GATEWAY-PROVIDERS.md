# Provider Gateway architecture

Portfolio Architect keeps provider acquisition isolated from the Home Assistant integration. Every provider Gateway has a separate supervised Home Assistant App identity and private provider state while sharing the audited read-only REST/server contract.

## Common runtime boundary

The hardened server consumes only a bounded `provider_id`, a validated refresh interval and `fetch_snapshot()` returning REST-schema-1 provider-neutral data. Gateway health schema 6 adds only the non-secret `provider_id`; schemas 1 through 5 remain compatible.

Version 1.24.0 further moves server configuration and secret-file handling into provider-neutral runtime code. `GatewayState` and `create_server()` consume `ServerConfig` directly rather than the complete Comdirect configuration.

## Official App identities

| Provider | Display name | App slug | v1.24 state |
| --- | --- | --- | --- |
| Comdirect | Portfolio Architect Gateway — Comdirect | `portfolio_architect_gateway` | stable live provider |
| DKB | Portfolio Architect Gateway — DKB | `portfolio_architect_gateway_dkb` | experimental provider shell |
| Trade Republic | Portfolio Architect Gateway — Trade Republic | `portfolio_architect_gateway_trade_republic` | experimental provider shell |

The Comdirect slug is retained permanently so existing credentials, OAuth/session state, selected account, cash policy, API token and cached snapshot remain in place. DKB and Trade Republic have distinct slugs, therefore Supervisor gives each an independent App identity and private `/data` volume.

No DKB or Trade Republic acquisition runtime is shipped by v1.24.0. The DKB/TR packages are deliberately `manual_only` and experimental in v1.24.0. They can be installed and started for package/isolation acceptance, but `fetch_snapshot()` fails closed with a configuration error and `/api/v1/portfolio` has no snapshot to serve. Their admin-only Ingress page states explicitly that live acquisition is not yet implemented.

Version 1.24.1 fixes the shell startup packaging discovered during v1.24.0 live acceptance. The common server no longer requires the Comdirect-only configuration module at runtime, and protected CI now starts both reduced shell containers before publication. No provider acquisition capability is added.

## Shared source and packaging rule

Home Assistant builds each App from its own directory. To avoid independent implementations drifting, the repository keeps one canonical Gateway Python source tree under `gateway/src/portfolio_architect_gateway`. The Comdirect App vendors the complete canonical package. DKB/TR vendor only the audited provider-neutral subset required by the shell. `tools/sync_gateway_app_sources.py` performs synchronization and regression tests require byte identity.

Physical copies in App build contexts are packaging copies, not independent forks of the runtime. Provider-specific acquisition/authentication/parsing modules are not copied into unrelated provider Apps.

## Isolation rules

Credentials, sessions, selected accounts, imported source documents, caches and provider diagnostics are never shared between provider Apps. Provider-specific inputs are transformed into the common snapshot model only after provider validation succeeds. The common REST server does not parse provider documents or perform provider authentication.

The REST service remains bearer-authenticated and GET-only. No provider App may gain order, trade, transfer, payment or transaction-history write capabilities merely because its upstream provider offers them.

## Next provider milestone

Portfolio Architect v1.25.0 will implement supported Trade Republic statement-document import inside the already separate Trade Republic App. Real documents remain private input; public regression fixtures must be wholly synthetic. DKB live acquisition remains a later provider-specific design.
