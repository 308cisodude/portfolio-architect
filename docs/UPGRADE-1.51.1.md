# Upgrade to Portfolio Architect 1.51.1

Version 1.51.1 is a narrow Home Assistant integration hotfix for the live-observed
v1.51.0 entity-attribute regression. It does not change Gateway acquisition,
wire schemas, planner economics, freshness, security, or the Generic Import
Gateway architecture introduced by v1.51.0.

## What is fixed

v1.51.0 correctly removed the final Home Assistant-side local mapped-CSV
acquisition path, including the coordinator's `local_paths` state. One stale
presentation/diagnostic branch remained in `PortfolioArchitectCoordinator.configuration_label`.
When Home Assistant evaluated source attributes for Portfolio Architect entities,
that branch attempted to access the removed `self.local_paths` member and raised
`AttributeError`, causing many entities to appear unavailable even though the
integration itself had loaded.

v1.51.1 removes the obsolete local-file coordinator references and keeps the
remaining deprecated legacy-sensor metadata bounded without reintroducing any
CSV acquisition code. The normal schema-12 all-Gateway source attributes now
evaluate without a `local_paths` member.

## Upgrade procedure

1. Update **Portfolio Architect** through HACS to **1.51.1**.
2. Restart Home Assistant once.
3. Confirm the existing config entry remains schema 12 and the configured
   Comdirect, Trade Republic and DKB sources return healthy exactly once.
4. Confirm previously unavailable plan/source/presentation entities recover.
5. Run the established acquisition/freshness template and confirm Comdirect
   remains `live_api / 24 h`, Trade Republic remains
   `imported_statement / 336 h`, and DKB remains `csv / 336 h` under the current
   monthly policy.
6. Align the four Gateway App packages to **1.51.1** for version hygiene if
   desired. Their runtime/acquisition behavior is unchanged from v1.51.0 and no
   provider state needs to be reset.

Do not reauthenticate Comdirect, re-import DKB/Trade Republic evidence, install
or import into the Generic Import Gateway merely to repair this defect, remove
or recreate Portfolio Architect sources, or replace the dashboard.

## Compatibility and preserved boundaries

- config-entry schema 12: unchanged
- portfolio payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 7: unchanged; schemas 1-6 remain supported
- presentation schema 2: unchanged
- broker schemas 1/2/3: unchanged
- Comdirect `live_api`/`csv` no-fallback arbitration: unchanged
- DKB CSV and Trade Republic PDF acquisition: unchanged
- Generic Import Gateway mapped-CSV acquisition: unchanged
- v1.48 acquisition-aware freshness and explicit user thresholds: unchanged
- independent holdings/cash evidence clocks: unchanged
- verified private-PKI HTTPS, bearer authentication and DNS pinning: unchanged
- source-set atomicity and Home Assistant LKG: unchanged
- planner, funding topology and execution-path semantics: unchanged
- DKB anonymous FinTS probe and authenticated-acquisition gate: unchanged
- no trading, order, transfer, payment, transaction-history, sell or withdrawal
  capability is added

No dashboard YAML replacement is required.
