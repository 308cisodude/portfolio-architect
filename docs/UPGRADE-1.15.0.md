# Upgrade to Portfolio Architect 1.15.0

Version 1.15.0 adds bounded, native explainability entities for allocation state,
purchase recommendations, and active policy decisions. Calculations, the ±1 pp
corridor, source handling, credentials, schemas, caches, and existing entity IDs
remain unchanged.

## Integration update

Upload `portfolio-architect-v1.15.0-ha-dropin.zip` to `/config`, back up the
current component and Portfolio Architect data directory, extract the archive over
`/config`, run `ha core check`, and restart Home Assistant.

After restart, verify `sensor.portfolio_architect_version` reports `1.15.0` and
that the new per-position explanation entities are available.

## Dashboard update

Replace the complete raw Portfolio Architect dashboard configuration with
`portfolio-architect-v1.15.0-bilingual-dashboard.yaml`.

The dashboard keeps its existing native layout and changes only interaction targets:

- tapping a drift tile opens a bounded allocation explanation;
- tapping a purchase tile still opens the copy-friendly ISIN entity;
- holding a purchase tile opens a bounded purchase explanation;
- tapping an active policy finding opens a bounded policy decision;
- the accepted Robotics exception continues to open its compact exception detail.

No restart is required after replacing the dashboard YAML.

## Gateway App

The Gateway runtime is unchanged. Updating the v1.15.0 App in place is optional
and exists for package-version alignment only. Do not uninstall the App or remove
its private data.

## Rollback

Restore the v1.14.1 integration drop-in and dashboard YAML, run `ha core check`,
and restart Home Assistant. No configuration or data migration needs reversal.
