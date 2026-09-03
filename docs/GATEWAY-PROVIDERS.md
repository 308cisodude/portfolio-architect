# Provider Gateway architecture

Portfolio Architect keeps provider acquisition isolated from the Home Assistant
integration. Every provider Gateway has a separate supervised Home Assistant App
identity and private provider state while sharing the audited read-only REST/server
contract.

## Common runtime boundary

The hardened server consumes only a bounded `provider_id`, validated acquisition
metadata and `fetch_snapshot()` returning REST-schema-1 provider-neutral data.
Gateway health schema 9 adds the bounded acquisition control plane (active method, method readiness/inventory, explicit no-fallback policy and operator switch history); schema 7 retains bounded `acquisition_mode`, schema 6 carries bounded provider identity, and schemas 1 through 7 remain accepted for compatibility.

Provider-specific authentication/parsing stays inside its own App. Portfolio
Architect consumes only canonical Gateway snapshots and never parses official or
generic acquisition formats itself.

## Official App identities and current maturity

| Capability owner | Display name | App slug | v1.56.1 maturity |
| --- | --- | --- | --- |
| Comdirect | Portfolio Architect Gateway — Comdirect | `portfolio_architect_gateway_comdirect` | **stable** — live API or explicit static CSV, auto-start |
| DKB | Portfolio Architect Gateway — DKB | `portfolio_architect_gateway_dkb` | **stable** — depot/cash CSV, auto-start; anonymous FinTS probe remains experimental/research-only |
| Trade Republic | Portfolio Architect Gateway — Trade Republic | `portfolio_architect_gateway_trade_republic` | **stable** — DEPOTAUSZUG/KONTOAUSZUG PDF import, auto-start |
| Generic Import | Portfolio Architect Gateway — Generic Import | `portfolio_architect_gateway_import` | **stable** — provider-neutral multi-profile mapped CSV + optional EUR cash, auto-start |

The provider-qualified Comdirect slug `portfolio_architect_gateway_comdirect` is canonical from v1.55.1 onward after the controlled identity migration. The historical `portfolio_architect_gateway` package was labelled **Comdirect LEGACY** and deprecated through its final v1.56.x migration-source line, then withdrawn from the active App repository in v1.57.0. An already-installed supported v1.55/v1.56 Legacy instance can still use the unchanged explicit same-CA/bearer migration receiver in canonical Comdirect; the historical slug is not reused. Every active provider App has a distinct slug and independent App-private `/data` volume.

The DKB App-level stable marker applies only to its live-proven CSV holdings/cash
acquisition. It does not imply authenticated FinTS support. The anonymous BPD probe
remains a separately labelled research capability and cannot replace, refresh or
silently fall back from CSV evidence.

Trade Republic's supported local PDF acquisition is stable. Generic Import remains
experimental until deliberate live exercise establishes the same operational
evidence; its fixed provider identity is `generic_csv` and it cannot impersonate an
official provider.

Historical provider evolution remains documented below: Trade Republic statement
import arrived in v1.25/v1.41, DKB CSV acquisition in v1.45/v1.47, Comdirect static
CSV in v1.48, and Generic Import in v1.51.

No DKB or Trade Republic acquisition runtime is shipped by v1.24.0; that historical release created only isolated provider shells.

## v1.53 acquisition-method control plane

Provider identity and acquisition method are deliberately separate. One provider Gateway may advertise several methods, but Portfolio Architect still consumes one canonical provider snapshot. The provider App owns preparation and activation. Portfolio Architect receives the control state read-only through health schema 9.

Comdirect is the first switchable implementation: `live_api` and `csv` may be prepared independently, inactive CSV requires both holdings and cash evidence before activation, and explicit switching is crash-safe/atomic with `fallback_policy: none`. Interrupted activation restores the prior mode and invalidates any ambiguous canonical cache before startup refresh; malformed inactive CSV candidate state is merely not-ready and cannot disrupt the active live method. DKB advertises `csv` plus non-activatable research-only `fints`; Trade Republic advertises `pdf` plus non-activatable unavailable `live_api`; Generic Import is fixed `csv`.

Health schema 9 (introduced in v1.58.0) now models authority independently per capability. The current live-accepted providers still use one method for both holdings and cash—Comdirect `live_api` on the current configuration, DKB `csv`, and Trade Republic `pdf`—but the model can represent a separately justified supplemental authority without duplicating the provider in Portfolio Architect. Any future mixed-method provider configuration remains evidence-gated, explicit and `fallback_policy: none`; authenticated DKB FinTS is not enabled by this capability model. v1.60.0 additionally displays the evidence clock of the canonical snapshot currently published for each capability, never staged inactive evidence. v1.61.0 is Home Assistant-side Configure UX only; Gateway authority and wire contracts are unchanged. v1.61.1 completes the Home Assistant Supervisor-discovery lifecycle provider-neutrally: any validated official Gateway may bootstrap the singleton Portfolio Architect entry on a fresh installation, concurrent first-run discoveries collapse onto that one integration unique ID, and after the entry exists every unconfigured provider is retained only as an internal candidate instead of opening another top-level Add flow. Gateway runtime and authority remain unchanged.
v1.61.2 changes only the Home Assistant Configure presentation fallback for the primary Gateway identity; provider acquisition, health schema 9 and all Gateway wire/security contracts remain unchanged.

## Shared source and packaging rule

Home Assistant builds each App from its own directory. To avoid independent
implementations drifting, the repository keeps one canonical Gateway Python source
tree under `gateway/src/portfolio_architect_gateway`. The Comdirect App vendors the
complete canonical package. DKB/TR/Generic Import vendor only the audited provider-neutral subset
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
remains unchanged and provider-neutral. The historical PA-side `dkb_csv` identity was
kept distinct from Gateway identity `dkb` during migration; v1.46.0 retires that
legacy source identity from the current runtime after the cut-over was live-proven.

## Trade Republic v1.25 import boundary

The Trade Republic App accepts only the documented German text-PDF `DEPOTAUSZUG`
family. The original PDF is never persisted; only the canonical holdings snapshot
is stored under the App-private `/data/gateway` volume. `pypdf` is a
Trade-Republic-App-only, hash-pinned build dependency and is not introduced into
Comdirect, DKB, the standalone Gateway, or the Home Assistant integration.

The historical statement above predates v1.45.0. DKB holdings are now supplied by bounded local CSV acquisition inside the DKB Gateway; authenticated FinTS holdings remain a later provider-specific gate after product registration and authenticated user-capability validation.

## DKB v1.47 Girokonto cash-evidence boundary

Version 1.47.0 mirrors the established Trade Republic holdings/cash separation without introducing a remote DKB API. The DKB App accepts the native Girokonto `Umsatzliste` CSV through admin-only Ingress, extracts only the explicit dated EUR `Kontostand`, and persists only normalized balance/date evidence. Account identifiers, transaction rows, counterparties, references and raw CSV bytes remain transient.

DKB depot holdings and Girokonto cash remain independently timestamped. Holdings keep `gateway_snapshot` freshness; cash uses the `imported_statement` freshness policy. A negative balance authorizes zero investment cash and no overdraft or credit facility is inferred. The common REST schema remains version 1 and FinTS remains isolated.

## v1.32 provider freshness and diagnostic foundation

Version 1.32.0 leaves provider acquisition and wire schemas unchanged while formalizing
`docs/PROVIDER-DIAGNOSTICS.md`. Provider diagnostics share one security policy but not one
retention mechanism: DKB's anonymous FinTS probe may retain its bounded response fingerprint,
Comdirect's authenticated traffic remains limited to bounded classifications/reasons, and
Trade Republic retains only the latest allowlisted statement-import outcome without storing
or fingerprinting the private PDF.

On the Home Assistant side, per-source freshness evidence is additive observability only.
The oldest contributing source remains the authoritative aggregate freshness gate; provider
classification does not introduce a different age limit or make a stale plan actionable in
v1.32.0.


## v1.33 source-freshness and plan-schedule separation

Version 1.33.0 leaves provider acquisition and wire schemas unchanged while Home Assistant
evaluates each source against an explicit bounded evidence-kind age policy independently from
recurring plan review dates. Version 1.33.1 changes only the Home Assistant recurring-schedule anchor. Version 1.34.0 adds
generic target identity/presentation architecture in the Home Assistant/engine layer; Provider Apps
receive package/User-Agent alignment only and the v1.32 diagnostic evidence policy remains
authoritative.


v1.62.0 adds health schema 10 `provider_name` and Supervisor discovery transport schema 2 for exact per-profile paths. One Generic App may expose up to eight isolated logical providers while Portfolio Architect continues to consume one canonical snapshot per provider; holdings/cash are never merged inside the Gateway. Existing `generic_csv` state retains its identity for compatibility. v1.62.1 changes ownership of first-run lifecycle: the Portfolio Architect integration must be initialized first, while ready Gateway discoveries are retained as source candidates for that existing singleton service. v1.62.2 leaves that transport unchanged and only hardens explicit first-run choices plus the Generic READY-profile colour presentation. Gateway acquisition and wire contracts are unchanged.
