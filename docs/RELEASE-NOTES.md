# Portfolio Architect v1.61.1 release notes

v1.61.1 is a narrow Home Assistant-side Supervisor-discovery lifecycle hotfix prepared from the exact published v1.61.0 baseline. It fixes the issue exposed during v1.61.0 live acceptance—an unconfigured supplemental Gateway could create another top-level **Discovered → Portfolio Architect → Add** card—and removes the inherited Comdirect-only first-run bootstrap assumption.

## Provider-neutral singleton bootstrap

Portfolio Architect still creates exactly one canonical Home Assistant config entry. On a fresh installation, however, **any validated Portfolio Architect Gateway may bootstrap that entry**. Comdirect is not mandatory. DKB, Trade Republic, Comdirect and a healthy Generic Import Gateway all use the same verified Supervisor-discovery bootstrap path.

The first configured Gateway becomes the **primary REST Gateway** only because its transport is stored in config-entry data; it has no provider-preference semantics. Supervisor supplies the endpoint/private-CA trust, while the operator supplies the App-private bearer token and Portfolio Architect configuration directory. Setup completes only after verified HTTPS, exact provider identity, healthy Gateway state and a usable portfolio snapshot validate.

All first-run discoveries claim the same `INSTANCE_UNIQUE_ID`. Home Assistant therefore collapses concurrent provider discoveries to one visible Portfolio Architect Add flow. Discovery is remembered before that singleton claim, so other providers that arrive while the first flow is in progress remain internal provider-keyed candidates. Once the first source is configured, those candidates can be adopted through the existing Options flow instead of creating competing integration instances.

## Existing-entry discovery suppression

Once the canonical Portfolio Architect config entry exists, a newly discovered unconfigured Gateway can no longer open a second Portfolio Architect Add flow. Supervisor discovery is retained only as an internal, in-memory candidate keyed by immutable `provider_id`.

Unconfigured candidates are exposed only inside the existing entry at **Configure → Portfolio sources → Additional REST Gateways → Add discovered REST Gateway**. Selecting a candidate is non-destructive. Portfolio Architect still requires that Gateway's App-private bearer token and then validates:

- the Supervisor-discovered verified-HTTPS endpoint and private CA;
- exact provider identity;
- primary and supplemental Gateway health;
- reauthentication/snapshot availability;
- snapshot timestamp, position count and SHA-256 integrity metadata;
- duplicate provider and endpoint exclusion.

Only after those checks pass is the supplemental source written to the existing config-entry options. No second Portfolio Architect config entry or provider-specific PA unique ID is created.

Repeated discovery for the same provider replaces the prior in-memory candidate instead of multiplying candidates. A candidate is removed when the provider becomes configured. The candidate path is now provider-neutral: if DKB or Trade Republic is primary, a later Comdirect discovery may be offered as a supplemental candidate rather than being discarded by a Comdirect-specific filter.

## Preserved discovery and migration behavior

The correction changes initial eligibility and unconfigured-provider routing only. Established secured-source paths remain intact:

- bounded legacy primary HTTP → verified-HTTPS migration;
- bounded supplemental HTTP → verified-HTTPS migration;
- explicit historical → provider-qualified Comdirect App endpoint migration;
- trust-change refusal for already-secured sources.

Configured Gateways therefore keep their existing migration/trust handling. The single-entry invariant is preserved both before and after setup.

## Security and compatibility boundary

The in-memory candidate registry contains only Supervisor discovery material already intended for local trust bootstrapping: provider identity, local endpoint identity, public private-CA certificate/fingerprint and related bounded discovery fields. It does not contain the App bearer token or provider credentials. Bearer material is supplied only through the existing Portfolio Architect Options flow when the operator explicitly adopts a candidate.

This release does not change provider acquisition, Gateway runtime, Gateway health schema 9 or schemas 1–8 compatibility, REST portfolio schema 1, Portfolio payload schema 8, config-entry schema 12, canonical evidence clocks, freshness, `fallback_policy: none`, LKG/anti-rollback/source-set atomicity, DNS pinning, planner economics, funding topology, dashboard YAML, or the advisory-only boundary. Authenticated DKB FinTS remains disabled/research-only. There is no trading, order, transfer, payment, transaction-history, sell or withdrawal capability.
There is **no silent fallback** between acquisition methods. The historical **Comdirect LEGACY** App remains removed from the active repository; canonical Comdirect retains only its bounded migration receiver for already-installed supported Legacy instances.

All four official Gateway App packages are version-aligned to v1.61.1 for release hygiene only; their runtime behavior is unchanged from v1.61.0.

## Preserved compatibility contracts

The preserved compatibility contracts remain explicit:

- Portfolio payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 9 current; schemas 1–8 remain supported;
- historical early compatibility remains explicit: schemas 1–6 remain supported;
- presentation schema 2: unchanged;
- broker schemas 1/2/3: unchanged;
- config-entry schema 12: unchanged;
- acquisition authority and `fallback_policy: none`: unchanged;
- canonical capability evidence clocks and freshness: unchanged;
- private-PKI HTTPS, bearer authentication and DNS pinning: unchanged;
- LKG, anti-rollback and source-set atomicity: unchanged;
- planner economics, funding-route semantics and advisory-only boundary: unchanged;
- authenticated DKB FinTS acquisition remains disabled;
- no dashboard YAML replacement is required.

No trading, order, transfer, payment, or transaction-history capability is introduced. Sell and withdrawal capability also remain absent.

## Historical compatibility notes retained

The historical v1.19.0-rc2 brokerage probe remains historical, is not included in this stable release, and is not promoted by this release. The v1.39 colourful allocation view was not included in v1.38.1; that historical sequencing remains documented and unchanged.

Trade Republic provider-specific statement parsing remains inside its Gateway; v1.61.1 does not move PDF parsing into Portfolio Architect.

The v1.33.0 source-freshness and plan-schedule separation remains intact: recurring scheduling remains anchored to the latest valid Portfolio Architect evaluation and this release does not change any configured freshness threshold. Acquisition authority remains explicit with `fallback_policy: none`; there is no silent fallback between methods.
