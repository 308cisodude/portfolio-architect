# Upgrade to Portfolio Architect v1.62.1

v1.62.1 completes the v1.62 Generic Import graduation by making **Portfolio Architect itself own first-run initialization**. Gateway Apps remain acquisition-only components and never create or populate Portfolio Architect investment configuration.

## Why this patch exists

Live clean-room acceptance of v1.62.0 proved that a ready Generic profile was correctly withheld from discovery until validated holdings existed and could then be discovered as the sole provider. The final bootstrap step still assumed that `/config/portfolio-architect` and the four engine YAML documents already existed, which meant a genuinely new user had to provision configuration files by hand.

v1.62.1 removes that expert-only prerequisite without inventing investment assumptions.

## New installation sequence

For a new installation:

1. Install the Portfolio Architect integration.
2. Add **Portfolio Architect** under Home Assistant **Settings → Devices & services → Add integration**.
3. Initialize the Portfolio Architect-owned configuration directory. The default is `portfolio-architect` below `/config`.
4. Portfolio Architect creates its singleton config entry in a fail-closed **source required** state. It creates no portfolio source, target allocation, investment policy, instrument facts or execution provider.
5. Install/configure one or more Gateway Apps.
6. A ready Gateway is retained as a candidate for the already initialized Portfolio Architect service. Adopt the first source under **Configure → Portfolio sources**.
7. If no complete existing YAML configuration was supplied, Portfolio Architect enters **plan required** and offers **Complete initial setup**.
8. The native setup flow asks the user to explicitly select target instruments from source holdings with valid ISIN identity and to supply the plan, target weights, instrument-policy facts and policy thresholds. It does not prefill investment assumptions.
9. Only after the complete candidate validates does Portfolio Architect atomically write `portfolio.yaml`, `policy.yaml`, `instruments.yaml` and `broker.yaml`, switch the config entry to **configured**, reload, and create normal runtime entities.

Advanced users may point initialization at an already complete valid Portfolio Architect configuration directory. Existing files are preserved; partially populated or invalid existing configuration fails closed and is never rewritten automatically.

## Gateway discovery lifecycle

Gateway discovery no longer creates the Portfolio Architect service.

- With **no Portfolio Architect config entry**, a valid Supervisor discovery is remembered transiently and the discovery flow aborts with an initialization-required result.
- With one initialized PA entry and **no source**, ready Gateways are offered as candidates for the first source.
- With a configured source, the established v1.61 provider-keyed supplemental-candidate behavior, HTTP→HTTPS migration and Comdirect App-slug migration/trust rules remain unchanged.
- A stale in-progress v1.62.0 discovery-confirmation flow cannot create a service after v1.62.1 is installed.

The first source is still fully validated before adoption: verified HTTPS/trust, bearer authentication, exact provider identity, Gateway health, snapshot timestamp/count and SHA-256 integrity must agree.

## Setup states and config-entry schema 13

Config-entry schema 13 adds the explicit bounded setup states:

- `source_required`
- `plan_required`
- `configured`

Existing config entries migrate to `configured` and retain their current behavior. An incomplete entry deliberately loads without a coordinator or Portfolio Architect entities; bounded diagnostics remain available and no Gateway is contacted until the relevant setup stage is completed.

## No invented execution provider

The first native plan creates provider-aware broker schema 3 with an empty `providers` map and no funding edges. This is a valid explicit route-unavailable state. The user may later add execution providers and evidence-backed routes through the existing broker editor. An empty provider map is accepted only with an empty funding topology.

## Generic Import

The v1.62.0 stable multi-profile Generic Import behavior is unchanged. Existing `generic_csv` compatibility, generated `generic_<stable-id>` profiles, independent holdings/cash evidence clocks, raw-CSV privacy, profile paths, health schema 10 and discovery schema 2 remain intact.

For the native initial-plan wizard, a source holding must carry a valid ISIN to be eligible as a target-plan candidate. Holdings without ISIN remain valid whole-portfolio holdings but are not used to invent target identity.

## Existing installations

Normal v1.62.0/v1.61.x installations with a valid source and complete configuration migrate automatically to config-entry schema 13 as `configured`. No dashboard replacement, source migration, broker migration or Gateway reauthentication is required.

All four active Gateway Apps are version-aligned to 1.62.1 for release hygiene; their acquisition behavior is unchanged from v1.62.0.

## Preserved boundaries

REST portfolio schema 1, Portfolio payload schema 8, health schema 10 with schemas 1–9 compatibility, discovery schemas 1/2, presentation schema 2, canonical evidence/freshness, `fallback_policy: none`, private-PKI HTTPS, bearer authentication, DNS pinning, LKG/anti-rollback/source-set atomicity, planner/funding semantics and advisory-only execution boundaries remain intact. Authenticated DKB FinTS remains disabled/research-only.
