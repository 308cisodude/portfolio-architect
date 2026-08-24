# Portfolio Architect 1.51.1

Portfolio Architect v1.51.1 is a narrow Home Assistant integration correctness
hotfix for a live-observed v1.51.0 regression. The v1.51.0 Generic Import Gateway
architecture remains intact and no provider acquisition or wire contract changes.

## Coordinator source-attribute hotfix

v1.51.0 intentionally removed the final Home Assistant-side local mapped-CSV
acquisition path and its coordinator `local_paths` state. A stale
`configuration_label` branch still referenced `self.local_paths` while entity
attributes were being calculated. On a normal schema-12 all-Gateway installation,
Home Assistant therefore raised `AttributeError` during entity state evaluation
and many Portfolio Architect entities appeared unavailable.

v1.51.1 removes that stale dependency and also eliminates the remaining dead
`local_paths`/`csv_source_config` coordinator references so unavailable-startup and
deprecated legacy-sensor metadata cannot traverse attributes removed by the
v1.51 architecture cleanup. The fix does not restore local CSV parsing or create
an implicit Generic Import dependency.

Executable regression coverage evaluates the exact production
`configuration_label` property and `_source_attributes()` body against an
all-Gateway coordinator-shaped object that deliberately has no `local_paths`
member.

## Preserved architecture

Trade Republic provider-specific statement parsing remains isolated in its Gateway; this hotfix does not move PDF parsing into Portfolio Architect.

The dedicated **Portfolio Architect Gateway — Generic Import** remains the only
provider-neutral mapped-CSV acquisition path. Comdirect `live_api`/`csv`
arbitration, DKB CSV holdings/cash acquisition, Trade Republic statement
acquisition, DKB probe timestamp behavior, v1.48 cadence-aware freshness,
independent evidence clocks, provider-scoped cash, funding topology, planner
economics, private-PKI transport, DNS pinning, configured-source atomicity and
Home Assistant LKG are unchanged.

Compatibility remains explicit:

- config-entry schema 12: unchanged
- portfolio payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 7 current; schemas 1–6 remain supported
- presentation schema 2: unchanged
- broker schemas 1/2/3: unchanged


The historical v1.19.0-rc2 brokerage-probe state remains historical and is not promoted by this release.

The v1.33.0 source-freshness and plan-schedule separation remains anchored to the latest valid Portfolio Architect evaluation; this hotfix does not change any configured freshness threshold, and evidence age and recurring plan scheduling stay independent. The historical v1.39 colourful allocation view was not included in v1.38.1; that release sequencing remains documented.


No trading, order, transfer, payment, or transaction-history capability is introduced; sell and withdrawal capability remain absent. authenticated DKB FinTS acquisition remains disabled.
No dashboard YAML replacement is required.
