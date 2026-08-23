# Upgrade to Portfolio Architect 1.46.0

Version 1.46.0 retires the completed Home Assistant-side DKB CSV migration bridge. It does not change portfolio calculations, DKB Gateway CSV parsing, normal snapshot freshness, FinTS capability, broker configuration or dashboard presentation.

## Required prerequisite

Before installing v1.46.0, DKB must already be represented through **Portfolio Architect Gateway — DKB** (`provider_id: dkb`). If the current Portfolio Architect configuration still contains a legacy `dkb_csv` source or non-empty supplemental DKB CSV paths, remain on **v1.45.1** and complete that release's verified migration first.

Schema 10 fails closed rather than silently deleting an active legacy DKB source.

## Upgrade order

1. Confirm Portfolio Architect is healthy on v1.45.1 and DKB is supplied by the DKB Gateway, not by a legacy PA-side CSV source.
2. Update the Portfolio Architect Home Assistant integration to **1.46.0** and restart Home Assistant once.
3. Confirm the integration loads normally and DKB remains a verified-HTTPS `provider_id: dkb` contributor.
4. Align the Comdirect, DKB and Trade Republic Gateway Apps to **1.46.0** in place. Preserve each App's private `/data` state.
5. Confirm source/provider counts, DKB holdings/quantity/freshness, Comdirect and Trade Republic data, cash routing and the current plan are unchanged.
6. No dashboard YAML replacement or broker configuration migration is required.

## What is intentionally gone

The current Home Assistant integration no longer contains or exposes:

- the provider-specific DKB CSV parser;
- legacy DKB CSV source creation/editing;
- supplemental DKB CSV path aggregation;
- the v1.45 DKB discovery equivalence/cut-over flow; or
- the v1.45.1 migration-only snapshot client/server endpoint.

DKB CSV upload remains fully supported through the DKB Gateway's protected Ingress UI. The raw export and depot identity remain transient and only the normalized canonical snapshot is persisted.

## Rollback note

Do not roll back to a release that expects PA-side DKB CSV ownership as a substitute for the Gateway source. The v1.45.1 migration should already have removed that source from the live config entry. App-private DKB snapshot state is unaffected by this integration cleanup.
