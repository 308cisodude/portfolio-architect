# Portfolio Architect v1.62.0 release notes

v1.62.0 graduates **Portfolio Architect Gateway — Generic Import** from experimental to stable and turns it into a supported standalone or supplemental provider for users whose institution has no dedicated Portfolio Architect Gateway.

The release also removes the former one-logical-provider limitation before the Generic contract becomes stable: one Generic Import App can host up to eight independent source profiles. Portfolio Architect still consumes ordinary provider-shaped Gateway snapshots; it does not receive a special multi-provider payload.

## Stable multi-profile Generic Import

Each new Generic profile has:

- an immutable randomly allocated `generic_<stable-id>` provider identity;
- a separately editable human provider name;
- its own CSV mapping;
- its own normalized canonical holdings snapshot;
- optional provider-local EUR investment cash;
- independent holdings and cash evidence timestamps;
- bounded privacy-safe action diagnostics; and
- its own authenticated REST portfolio/health paths under the shared Generic App private-PKI origin.

An existing experimental Generic Import installation is migrated conservatively: if legacy Generic state exists, the first migrated profile retains provider identity `generic_csv`, its existing private snapshot/mapping/diagnostic files, and the legacy `/api/v1/portfolio` REST path. No remove/re-add or provider-identity substitution is required solely because of the upgrade.

## Import and persistence semantics

Raw CSV bytes are parsed transiently and are never persisted. The App does not persist upload filenames, unmapped columns, source rows, account identifiers or other raw document material.

A successful holdings import validates the complete candidate before publishing it and atomically replaces only the selected profile's normalized canonical holdings. Independently recorded cash is retained. A rejected import leaves the last valid canonical snapshot unchanged.

Optional investment cash is entered separately as a non-negative EUR amount. Its submission time is the independent cash evidence timestamp; changing or clearing cash does not change the holdings evidence timestamp. Holdings must exist before cash can be recorded.

Profiles survive normal App restarts through cold-backup-compatible `/data` state. Renaming a profile changes only its human label; the immutable provider ID is unchanged. Profile deletion is explicit, two-step in the Ingress UI and scoped to that profile's normalized private state. The Generic App deliberately retains no Home Assistant API privilege, so an adopted profile must be removed from Portfolio Architect before deleting it from the App.

## Discovery and wire contracts

A Generic profile is advertised through Home Assistant Supervisor discovery only after it has a validated holdings snapshot. Each ready profile is published separately.

Supervisor discovery transport schema 2 adds:

- the exact provider-specific REST path; and
- a bounded human `provider_name`.

Existing fixed-provider discovery schema 1 remains supported and unchanged.

Gateway health schema 10 adds the bounded human `provider_name`; schemas 1–9 remain supported. The immutable `provider_id` remains the security and portfolio identity. Portfolio Architect verifies requested provider identity against health and snapshot integrity exactly as for native providers.

One shared private CA and App-level bearer token protect the Generic App origin. Profiles remain logically isolated because each path is bound to one immutable provider identity; holdings and cash from different Generic profiles are never merged inside the Gateway.

## Portfolio Architect integration changes

Portfolio Architect negotiates health schema 10 and uses `provider_name` for presentation while preserving `provider_id` as canonical identity. The bounded supplemental REST-source limit rises from four to eight so multi-profile Generic sources can coexist with native providers without changing the singleton config-entry architecture.

A fresh installation can be bootstrapped by a ready Generic profile through the provider-neutral discovery lifecycle introduced in v1.61.1. Once the singleton PA entry exists, additional ready Generic profiles remain internal discovered candidates until explicitly adopted under **Configure → Portfolio sources → Additional REST Gateways**.

## Preserved boundaries

Comdirect, DKB and Trade Republic acquisition behavior is unchanged. REST portfolio schema 1, payload schema 8, config-entry schema 12, acquisition authority, `fallback_policy: none`, evidence freshness, verified private-PKI HTTPS, bearer authentication, DNS pinning, LKG/anti-rollback/source-set atomicity, planner/funding behavior and advisory-only semantics remain intact.

The DKB anonymous FinTS capability probe remains experimental/research-only; authenticated DKB FinTS acquisition remains disabled and evidence-gated.

No trading, order, transfer, payment, or transaction-history capability is introduced by this release.

No dashboard YAML replacement is required.

## Preserved historical release invariants

For regression clarity, the following established contracts are explicitly preserved by v1.62.0:

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 10 is current; schemas 1–9 remain supported
- presentation schema 2: unchanged
- broker schemas 1/2/3: unchanged
- The v1.33.0 source-freshness and plan-schedule separation remains in force: recurring schedule anchoring uses the latest valid Portfolio Architect evaluation and this release does not change any configured freshness threshold.
- Trade Republic provider-specific PDF parsing stays in its Gateway; this release does not move PDF parsing into Portfolio Architect.
- The historical `v1.19.0-rc2` brokerage-probe idea is not promoted by this release.
- Comdirect LEGACY was removed from the active repository in v1.57.0 and the historical slug is not reused.
- Acquisition remains explicit with no silent fallback.
- No trading, order, transfer, payment, or transaction-history capability is introduced.
- The v1.38.1 dynamic drift presentation is included through the established presentation schema; it is not included as a separate alternate calculation path.
