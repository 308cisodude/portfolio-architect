# Portfolio Architect 1.49.0

Portfolio Architect v1.49.0 completes the Comdirect acquisition-boundary cleanup started in v1.48.0. Complete Comdirect static CSV acquisition already lives inside **Portfolio Architect Gateway — Comdirect**; the Home Assistant integration no longer needs the temporary provider-specific Comdirect CSV parser that existed only as an exact-equivalence migration oracle during the v1.48 cut-over window.

## Legacy Comdirect CSV bridge retired

The current Home Assistant integration now keeps only the provider-neutral mapped-CSV adapter. Provider-specific Comdirect acquisition belongs entirely to the Comdirect Gateway.

v1.49.0 removes the production PA-side Comdirect depot-CSV parser, the current `comdirect_csv` source-provider/enum surface, and the Supervisor discovery migration step that compared a legacy local CSV source with a verified health-schema-7 Comdirect Gateway in explicit `csv` mode.

Config-entry schema **11** provides the fail-closed upgrade boundary. If a config entry still uses the historical Home Assistant-side `comdirect_csv` source, migration stops without changing the source. The operator must remain on v1.48.2, complete the verified Gateway cut-over there, and then update to v1.49.0. No source is silently reinterpreted or discarded.

Historical upgrade and release documentation remains intact as audit history.

## Provider architecture after v1.49.0

Provider-specific acquisition is now consistently outside Portfolio Architect for all three official providers:

- **Comdirect Gateway:** live API or explicit complete static CSV, mutually exclusive with no silent fallback;
- **DKB Gateway:** depot CSV holdings plus independent Girokonto CSV cash; and
- **Trade Republic Gateway:** local holdings/cash PDF statement families.

Portfolio Architect itself retains only the provider-neutral generic mapped-CSV escape hatch. A later architecture milestone will move that remaining generic import capability into a dedicated import Gateway as well.

## Provider packages

The Comdirect, DKB and Trade Republic Apps are version-aligned to 1.49.0. Provider runtime/acquisition behavior is unchanged from the live-accepted v1.48.2 baseline. No CSV/PDF re-import, Comdirect PhotoTAN reauthentication, source migration or dashboard replacement is required for an already Gateway-backed installation.

## Historical compatibility contracts retained

The v1.33.0 source-freshness and plan-schedule separation remains anchored to the latest valid Portfolio Architect evaluation; v1.49.0 does not change any configured freshness threshold. The v1.48.1 cadence-aware freshness policy and v1.48.2 acquisition-mode propagation remain unchanged. The historical v1.19.0-rc2 brokerage-probe state remains historical and is not promoted by this release. The historical v1.39 colourful allocation view was not included in v1.38.1; that sequencing remains documented. Trade Republic provider-specific statement parsing remains in its Gateway; this release does not move PDF parsing into Portfolio Architect. authenticated DKB FinTS acquisition remains disabled. No trading, order, transfer, payment, or transaction-history capability is introduced.

## Preserved boundaries

- portfolio payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 7 current; schemas 1–6 remain supported;
- presentation schema 2 and broker schemas 1/2/3: unchanged;
- Comdirect `live_api`/`csv` arbitration and no-fallback semantics: unchanged;
- DKB CSV and Trade Republic PDF acquisition/parsing: unchanged;
- v1.48 acquisition-aware freshness and explicit thresholds: unchanged;
- source-set atomicity, Home Assistant LKG, planner economics, funding topology and execution-path behavior: unchanged;
- verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-plaintext fallback: unchanged;
- no trading, order, transfer, payment, transaction-history, sell or withdrawal capability is added; and
- no dashboard YAML replacement is required.
