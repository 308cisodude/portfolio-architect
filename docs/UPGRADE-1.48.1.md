# Upgrade to Portfolio Architect 1.48.1

Version 1.48.1 corrects freshness classification for static Gateway acquisition and adds cadence-aware defaults for CSV/PDF evidence. It does not change provider acquisition, Gateway wire schemas, planner economics or the advisory-only boundary.

## Upgrade order

1. Start from the published v1.48.0 installation.
2. Update the Portfolio Architect Home Assistant integration to **1.48.1** and restart Home Assistant once.
3. Confirm the existing three provider sources return healthy with unchanged holdings, cash, planner economics and verified-HTTPS trust.
4. Align the Comdirect, DKB and Trade Republic Gateway Apps to **1.48.1** in place as normal package-version hygiene. Their provider runtime behavior is unchanged from v1.48.0.
5. No dashboard YAML replacement is required.

## Freshness behavior

Health-schema-7 acquisition mode is now authoritative for evidence classification:

- `live_api` -> live evidence;
- `csv` -> static CSV evidence;
- `pdf` -> static imported-statement evidence;
- no acquisition mode -> conservative established provider fallback.

For installations without explicit evidence-kind thresholds, defaults are:

- live / unknown Gateway: **24 hours**;
- weekly static CSV/PDF: **120 hours (5 days)**;
- monthly, quarterly or yearly static CSV/PDF: **336 hours (14 days)**.

Holdings and cash remain independently timestamped.

## Existing explicit thresholds are preserved

v1.48.1 does **not** silently replace values you have already saved under **Configure -> Runtime safeguards**. Existing explicit thresholds remain authoritative.

If an existing monthly installation deliberately wants the new recommended static policy, set both **Imported statement freshness** and **Imported CSV freshness** to **336 hours**. For a weekly plan, use **120 hours**. Keep the live API / Gateway threshold at **24 hours** unless there is a specific reason to override it.

A pre-v1.33 installation that still has only the old global threshold continues to use that threshold for every evidence family until provider-specific values are deliberately saved.

## Live acceptance

1. Verify health schema 7 is available from the aligned provider Apps and that the source summaries carry the expected acquisition modes.
2. On a monthly plan, confirm DKB `acquisition_mode: csv` uses the configured CSV threshold rather than the live/Gateway threshold.
3. Confirm Trade Republic `acquisition_mode: pdf` uses the statement threshold.
4. Confirm Comdirect in `live_api` remains on the live threshold; if deliberately switched to `csv`, it uses the CSV threshold for both independent static holdings and static cash evidence.
5. Confirm changing/refreshing cash does not alter holdings freshness and vice versa.
6. Confirm no source acquisition fallback, trading, transfer or order capability is introduced.
