# Portfolio Architect 1.48.2

Portfolio Architect v1.48.2 is a narrow Home Assistant-side hotfix for the acquisition-aware freshness path introduced in v1.48.1. Live acceptance showed that Gateway health schema 7 correctly reported DKB `acquisition_mode: csv`, but the coordinator discarded that mode when it replaced the enriched source summaries with acquisition-neutral aggregation summaries. DKB therefore still appeared as a generic `gateway_snapshot` and continued to use the 24-hour live/Gateway freshness threshold.

## Source-summary propagation fix

The coordinator now keeps acquisition mode attached to the same source summaries used by freshness evaluation, diagnostics, and Home Assistant entities:

- normal REST/multi-Gateway recalculation applies the validated primary and supplemental Gateway acquisition modes to the accepted aggregation summaries;
- the payload/LKG source summaries use the same annotation helper, preventing live-versus-LKG classification drift;
- a successful `304 Not Modified` primary refresh re-annotates the already accepted source summary from the newly observed Gateway health, so an App upgrade or deliberate mode change does not require a changed holdings snapshot merely to update freshness classification; and
- if a provider is explicitly re-observed without a usable acquisition mode, any older static annotation is removed or treated as `unknown`, preserving the conservative established provider fallback.

For the live regression fixture, an aligned DKB Gateway reporting schema-7 `acquisition_mode: csv` therefore reaches freshness as CSV evidence and uses the configured CSV threshold. Trade Republic `pdf` remains imported-statement evidence and Comdirect `live_api` remains live evidence.

## Freshness policy is unchanged from v1.48.1

v1.48.2 does not alter any freshness threshold or cadence rule. The v1.48.1 policy remains:

- live API / unknown Gateway default: **24 hours**;
- static CSV/PDF default for weekly plans: **120 hours / 5 days**;
- static CSV/PDF default for monthly, quarterly, or yearly plans: **336 hours / 14 days**;
- every explicitly configured evidence-kind threshold remains authoritative; and
- holdings and provider cash keep independent evidence clocks.

The current installation can therefore keep the deliberately configured monthly policy of 24 hours for live evidence and 336 hours for imported statement/CSV evidence.

## Provider packages

The Comdirect, DKB, and Trade Republic Apps are version-aligned to 1.48.2 only. Provider acquisition/runtime behavior is unchanged from v1.48.1/v1.48.0. No CSV/PDF re-import, Comdirect PhotoTAN reauthentication, source migration, or dashboard replacement is required solely because of this hotfix.

## Historical compatibility contracts retained

The v1.33.0 source-freshness and plan-schedule separation remains anchored to the latest valid Portfolio Architect evaluation; v1.48.2 does not change any configured freshness threshold. The historical v1.19.0-rc2 brokerage-probe state remains historical and is not promoted by this release. The historical v1.39 colourful allocation view was not included in v1.38.1; that sequencing remains documented. Trade Republic provider-specific statement parsing remains in its Gateway; this release does not move PDF parsing into Portfolio Architect. authenticated DKB FinTS acquisition remains disabled. No trading, order, transfer, payment, or transaction-history capability is introduced.

## Preserved boundaries

- portfolio payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 7 current; schemas 1–6 remain supported;
- presentation schema 2 and broker schemas 1/2/3: unchanged;
- Comdirect `live_api`/`csv` arbitration and no-fallback semantics: unchanged;
- DKB CSV and Trade Republic PDF acquisition/parsing: unchanged;
- source-set atomicity, Home Assistant LKG, planner economics, funding topology and execution-path behavior: unchanged;
- verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-plaintext fallback: unchanged;
- no trading, order, transfer, payment, transaction-history, sell, or withdrawal capability is added; and
- no dashboard YAML replacement is required.
