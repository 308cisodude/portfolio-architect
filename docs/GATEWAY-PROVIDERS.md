# Provider Gateway architecture

Portfolio Architect keeps provider acquisition isolated from the Home Assistant
integration. Every live provider Gateway is a separate supervised Home Assistant
App with private provider state and a common read-only Portfolio Architect REST
boundary.

## v1.23.0 foundation

Version 1.23.0 makes the existing Gateway runtime explicitly provider-aware before
additional providers are implemented.

The common hardened server consumes only this minimal provider contract:

- a bounded non-secret `provider_id`;
- a validated refresh interval; and
- a `fetch_snapshot()` operation returning REST-schema-1 provider-neutral data.

The common server no longer imports or type-depends on `ComdirectClient`. Provider
specific authentication, account discovery, cash semantics and bootstrap UI remain
inside the Comdirect implementation.

Gateway health schema 6 adds only `provider_id`. Health schemas 1 through 5 remain
available unchanged for older Portfolio Architect installations. Portfolio
Architect 1.23.0 requests schema 6 while advertising schemas 5 through 1 as
fallbacks, so an older supported Gateway continues to provide its richest known
health document.

## Official App identities

The provider App boundary is intentionally one App per provider:

| Provider | Display name | App slug |
| --- | --- | --- |
| Comdirect | Portfolio Architect Gateway — Comdirect | `portfolio_architect_gateway` |
| DKB | Portfolio Architect Gateway — DKB | `portfolio_architect_gateway_dkb` |
| Trade Republic | Portfolio Architect Gateway — Trade Republic | `portfolio_architect_gateway_trade_republic` |

The existing Comdirect slug is retained permanently for in-place migration of the
installed App. Renaming that slug would create a new Home Assistant App identity
and would unnecessarily strand the current private App data. The visible name can
change without changing the App identity.

No DKB or Trade Republic acquisition runtime is shipped by v1.23.0. Their names
and slugs are architecture reservations, not claims of supported connectivity.
They become installable only when their provider-specific acquisition path,
failure semantics, private persistence and acceptance tests exist.

## Isolation rules

Each provider App must own its own private App volume. Credentials, sessions,
selected accounts, imported source documents, caches and provider diagnostics are
never shared between provider Apps.

Provider-specific inputs may be transformed into the common snapshot model only
after their own validation succeeds. The common REST server receives the validated
provider-neutral result; it does not parse provider documents or perform provider
authentication.

The REST server remains GET-only. A provider adapter must not gain order, trade,
transfer, payment, transaction-history or other write capabilities merely because
its upstream provider offers them.

## Future provider rollout

The next provider-App work can reuse the common server/storage/model boundary but
must implement provider-specific behavior independently:

- **DKB:** choose a supported, local and privacy-preserving acquisition method and
  map it into the provider-neutral snapshot contract.
- **Trade Republic:** establish the separate App boundary first; statement-document
  import is the following milestone and must fail closed on unsupported or
  ambiguous documents.

Portfolio Architect currently supports one primary REST source plus its established
supplemental-source model. Supporting simultaneous primary REST Gateways is a
separate Home Assistant configuration/aggregation decision and must not be implied
by the provider-server refactor alone.
