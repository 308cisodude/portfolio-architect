# Provider Gateway architecture

Portfolio Architect keeps provider acquisition isolated from the Home Assistant
integration. Every provider Gateway has a separate supervised Home Assistant App
identity and private provider state while sharing the audited read-only REST/server
contract.

## Common runtime boundary

The hardened server consumes only a bounded `provider_id`, a validated refresh
interval and `fetch_snapshot()` returning REST-schema-1 provider-neutral data.
Gateway health schema 6 adds only the non-secret `provider_id`; schemas 1 through 5
remain compatible for the established single-primary path.

Version 1.24.0 moved server configuration and secret-file handling into
provider-neutral runtime code. `GatewayState` and `create_server()` consume
`ServerConfig` directly rather than the complete Comdirect configuration. Version
1.24.1 corrected reduced-package startup without widening this contract.

## Official App identities

| Provider | Display name | App slug | v1.26.2 state |
| --- | --- | --- | --- |
| Comdirect | Portfolio Architect Gateway — Comdirect | `portfolio_architect_gateway` | stable live provider, auto-start |
| DKB | Portfolio Architect Gateway — DKB | `portfolio_architect_gateway_dkb` | experimental manual-only fail-closed shell |
| Trade Republic | Portfolio Architect Gateway — Trade Republic | `portfolio_architect_gateway_trade_republic` | experimental statement-import provider, auto-start |

The Comdirect slug is retained permanently so existing credentials, OAuth/session
state, selected account, cash policy, API token and cached snapshot remain in place.
DKB and Trade Republic have distinct slugs, therefore Supervisor gives each an
independent App identity and private `/data` volume.

No DKB or Trade Republic acquisition runtime is shipped by v1.24.0; that release
created only the isolated provider shells.

Version 1.25.0 added only the Trade Republic provider-specific local statement
importer: before the first accepted `DEPOTAUSZUG` it remains degraded/unavailable;
after acceptance, `fetch_snapshot()` returns the persisted provider-neutral
snapshot and the common REST/health server operates normally. Version 1.26.0 changes
its boot policy to automatic because Portfolio Architect can now keep it configured
as an ongoing REST contributor. DKB remains manual-only and has no live acquisition
path.

## Shared source and packaging rule

Home Assistant builds each App from its own directory. To avoid independent
implementations drifting, the repository keeps one canonical Gateway Python source
tree under `gateway/src/portfolio_architect_gateway`. The Comdirect App vendors the
complete canonical package. DKB/TR vendor only the audited provider-neutral subset
required by their runtime. `tools/sync_gateway_app_sources.py` performs
synchronization and regression tests require byte identity.

Physical copies in App build contexts are packaging copies, not independent forks
of the runtime. Provider-specific acquisition/authentication/parsing modules are not
copied into unrelated provider Apps.

## Isolation rules

Credentials, sessions, selected accounts, imported source documents, caches and
provider diagnostics are never shared between provider Apps. Provider-specific
inputs are transformed into the common snapshot model only after provider
validation succeeds. The common REST server does not parse provider documents or
perform provider authentication.

The REST service remains bearer-authenticated and GET-only. No provider App may
gain order, trade, transfer, payment or transaction-history write capabilities
merely because its upstream provider offers them.

## Portfolio Architect aggregation boundary

Version 1.26.0 allows the Home Assistant integration to consume several independent
Gateway REST snapshots simultaneously. This does not connect the provider Apps to
one another. Each App remains a self-contained producer; Portfolio Architect is the
only aggregation point.

Version 1.26.1 does not change the provider App REST contract. It corrects the Home
Assistant-side identity model so an ISIN-only position (such as a Trade Republic
statement holding) satisfies the matching configured target by ISIN. WKN is used
only when ISIN is unavailable and may not override contradictory ISIN evidence.

Additional Gateways require health schema 6 so their bounded provider identity can
be verified before they join the aggregate. Provider IDs are provenance metadata,
not broker account identities. Source instances remain distinct from providers:
multiple source instances from the same provider count as multiple sources but one
distinct provider.

Configured additional REST sources participate atomically. If one fails, the
integration retains a matching previously validated complete aggregate as
non-actionable Home Assistant LKG instead of silently recalculating without that
provider.

Version 1.26.2 leaves that provider/Gateway contract unchanged. It adds only
privacy-safe source-failure presentation metadata in the Home Assistant integration
and explicit German dashboard presentation values.

## Trade Republic v1.25 import boundary

The Trade Republic App accepts only the documented German text-PDF `DEPOTAUSZUG`
family. The original PDF is never persisted; only the canonical holdings snapshot
is stored under the App-private `/data/gateway` volume. `pypdf` is a
Trade-Republic-App-only, hash-pinned build dependency and is not introduced into
Comdirect, DKB, the standalone Gateway, or the Home Assistant integration.

DKB live acquisition remains a later provider-specific design. The established DKB
CSV supplement can coexist with independent Comdirect and Trade Republic Gateway
REST snapshots in the v1.26 aggregate.
