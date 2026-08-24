# Upgrade to Portfolio Architect 1.48.2

Version 1.48.2 fixes the live coordinator propagation of health-schema-7 acquisition mode used by the v1.48.1 freshness policy. It does not change provider acquisition, configured freshness thresholds, planner economics, Gateway wire schemas, or the advisory-only boundary.

## Upgrade order

1. Start from the published v1.48.1 installation.
2. Update the Portfolio Architect Home Assistant integration to **1.48.2** and restart or reload Home Assistant as required by the normal HACS workflow.
3. Confirm the existing freshness settings remain unchanged.
4. Align the Comdirect, DKB, and Trade Republic Gateway Apps to **1.48.2** in place for package-version hygiene. Their runtime acquisition behavior is unchanged from v1.48.1.
5. Do not re-import DKB/Trade Republic evidence or reauthenticate Comdirect solely because of the upgrade.
6. No dashboard YAML replacement is required.

## Expected freshness classification

For an aligned health-schema-7 installation using the current monthly policy:

- Comdirect `acquisition_mode: live_api` -> `evidence_kind: live_api` -> **24 hours**;
- Trade Republic `acquisition_mode: pdf` -> `evidence_kind: imported_statement` -> **336 hours**; and
- DKB `acquisition_mode: csv` -> `evidence_kind: csv` -> **336 hours**.

The evidence timestamps themselves must not change merely because of the software upgrade. In particular, restarting/updating the DKB App must not make an existing static holdings CSV artificially newer.

## Live acceptance

After the integration and all three Apps are aligned:

1. Reload Portfolio Architect and allow one successful refresh.
2. Confirm `binary_sensor.portfolio_architect_data_fresh` is on and the effective thresholds remain 24/336/336/24 for live/statement/CSV/other on the deliberately configured monthly installation.
3. Confirm the per-source rows show Comdirect `live_api / 24`, Trade Republic `imported_statement / 336`, and DKB `csv / 336`.
4. Confirm provider count remains three, no unavailable/conflicting source is introduced, and planner actionability/economics remain unchanged.
5. Confirm Home Assistant LKG is inactive during healthy live operation.
6. No source fallback, trading, transfer, payment, or order capability is introduced.
