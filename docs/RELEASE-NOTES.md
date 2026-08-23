# Portfolio Architect 1.46.0

Portfolio Architect v1.46.0 completes the DKB CSV acquisition-boundary migration that was live-proven in v1.45.0/v1.45.1. Provider-specific DKB CSV parsing and source ownership now exist only inside **Portfolio Architect Gateway — DKB**; the temporary Home Assistant-side `dkb_csv` parser, supplemental-path source model, discovery cut-over flow, and migration-only REST endpoint are retired.

## DKB acquisition bridge retired

- The Home Assistant integration no longer parses DKB depot CSV files or offers DKB CSV source configuration.
- The old `dkb_csv` provider identity and supplemental DKB CSV path list are no longer active runtime source types.
- DKB Gateway discovery now follows the ordinary explicit supplemental-Gateway path; there is no special DKB-vs-legacy-CSV collision/migration branch.
- The one-shot `/api/v1/migration-snapshot` endpoint introduced in v1.45.1 is removed from the common Gateway and DKB App because the migration bridge it protected is no longer part of the current architecture.
- DKB depot CSV acquisition, newest-per-depot selection, same-date conflict rejection, exact Decimal valuation, transient depot identity, and normalized private persistence remain inside the DKB Gateway unchanged.

## Fail-closed schema-10 prerequisite

Config-entry schema 10 deliberately refuses to load an installation that still has an active legacy `dkb_csv` primary source or non-empty `supplemental_dkb_csv_paths`. Such an installation must first run v1.45.1, complete the verified DKB Gateway migration, and verify `provider_id: dkb` before upgrading.

Already-migrated installations advance normally; an empty obsolete supplemental-path option is removed during migration. No holdings source is silently discarded.

## Preserved boundaries

- portfolio payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged; schemas 1–5 remain supported;
- presentation schema 2 and broker schemas 1/2/3: unchanged;
- DKB Gateway CSV acquisition and the anonymous FinTS BPD capability probe: unchanged;
- authenticated DKB FinTS acquisition remains disabled;
- Comdirect acquisition/OAuth/session/cash behavior: unchanged;
- Trade Republic holdings/cash statement acquisition: unchanged; this release does not move PDF parsing into Portfolio Architect;
- source freshness policy, source-set atomicity, Home Assistant LKG, planner economics and execution-path behavior: unchanged;
- verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-plaintext fallback: unchanged;
- the historical v1.19.0-rc2 brokerage-probe state remains historical and is not promoted by this release;
- v1.33.0 source-freshness and plan-schedule separation remains anchored to the latest valid Portfolio Architect evaluation; this release does not change any configured freshness threshold;
- the historical v1.39 colourful allocation view was not included in v1.38.1; that release sequencing remains unchanged;
- No trading, order, transfer, payment, or transaction-history capability is added; sell and withdrawal capability remain absent as well;
- no dashboard YAML replacement is required.

This release deliberately leaves the provider-neutral generic mapped CSV adapter in Portfolio Architect. The next provider-specific acquisition migration is the existing Comdirect CSV path into **Portfolio Architect Gateway — Comdirect**.
