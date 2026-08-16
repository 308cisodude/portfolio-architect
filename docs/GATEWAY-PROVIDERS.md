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

| Provider | Display name | App slug | v1.29.0 state |
| --- | --- | --- | --- |
| Comdirect | Portfolio Architect Gateway — Comdirect | `portfolio_architect_gateway` | stable live provider, auto-start |
| DKB | Portfolio Architect Gateway — DKB | `portfolio_architect_gateway_dkb` | experimental manual-only anonymous FinTS capability probe; no live portfolio acquisition |
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
as an ongoing REST contributor. DKB remains manual-only. Version 1.28.0 added only
a registration-gated anonymous FinTS BPD capability probe; its provider REST snapshot
remains fail-closed and no live DKB acquisition path exists yet.

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

Version 1.26.7 leaves the provider/Gateway contract unchanged. It fixes only the common cached-snapshot and HTTP conditional-request layer: quantity-bearing snapshots reload byte-for-byte and ETag validation cannot be overridden by a date validator. v1.26.6 already corrected unavailable-source diagnostics so a REST Gateway observed in a non-live health mode is named even when that Gateway itself still serves a trusted cached
snapshot. Provider acquisition, authentication/private state, REST schema 1 and health
schema 6 are unchanged.

The v1.27 line hardens the shared internal transport. Every official App serves the
common REST/health API over verified HTTPS with a per-installation private CA while
retaining bearer authentication. The App publishes only public CA trust and bounded
provider/endpoint identity through Supervisor discovery. Version 1.27.2 corrects the
Home Assistant config-flow eligibility needed for an existing entry to consume that
discovery and migrate from legacy HTTP; Gateway runtime behavior is otherwise
unchanged from v1.27.1. Version 1.27.3 additionally keeps Gateway provider identity
separate from CSV importer identity: DKB Gateway is `dkb`, DKB CSV is `dkb_csv`,
and configured DKB CSV scope suppresses the DKB Gateway supplemental discovery
prompt. Version 1.27.4 keeps those transport/discovery contracts unchanged and adds
only Comdirect-provider session maintenance: a five-minute OAuth maintenance cadence
runs inside the Comdirect package independently of portfolio snapshot polling and
performs no provider-neutral portfolio acquisition. The common `PortfolioProvider`
contract remains free of OAuth/session assumptions. Private keys stay inside each App
and trust changes fail closed. REST schema 1 and health schema 6 remain unchanged.

## DKB v1.28 FinTS capability-probe boundary

Version 1.28.0 begins DKB acquisition research without adding DKB holdings to the
portfolio. The DKB App accepts only Portfolio Architect's own bounded FinTS product
registration number and can issue an anonymous FinTS 3.0 BPD dialog initialization
to DKB's fixed documented endpoint. It does not request a DKB login name, PIN or TAN.

The BPD response is reduced immediately to bounded capability metadata. The raw FinTS
response is not persisted or exposed. `HIWPDS` presence is treated only as bank-level
evidence that a securities-holdings transaction family is advertised; it does not
prove that an authenticated user's UPD permits the operation. A later release must
validate authenticated user capabilities and DKB-App decoupled authentication before
any holdings request can be considered.

The DKB App adds no external FinTS runtime library and no order, transfer, payment,
debit or transaction-history operation. The common `PortfolioProvider` contract
remains unchanged and provider-neutral. Existing DKB CSV identity `dkb_csv` stays
distinct from Gateway identity `dkb`, so the established collision/discovery rules
continue to prevent silent duplicate scope.

## Trade Republic v1.25 import boundary

The Trade Republic App accepts only the documented German text-PDF `DEPOTAUSZUG`
family. The original PDF is never persisted; only the canonical holdings snapshot
is stored under the App-private `/data/gateway` volume. `pypdf` is a
Trade-Republic-App-only, hash-pinned build dependency and is not introduced into
Comdirect, DKB, the standalone Gateway, or the Home Assistant integration.

DKB live holdings remain a later provider-specific gate after the v1.28 anonymous
BPD probe and authenticated user-capability validation. The established DKB CSV
supplement can coexist with independent Comdirect and Trade Republic Gateway REST
snapshots in the aggregate while the DKB Gateway itself remains non-live.
