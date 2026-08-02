# Upgrade from v0.5.3 to v0.5.4

v0.5.4 is a dashboard language-isolation and navigation-polish release.

## Changes

- view tabs are labelled `EN` and `DE`;
- donut view icons and the redundant language badge are removed;
- the target-architecture tile displays only the language-neutral `6 / 7`
  coverage summary;
- target-position native state strings are hidden and replaced by a
  language-specific legend;
- engine calculations, entity IDs, and rebalancing logic are unchanged.

## Upgrade

1. Back up the runtime and complete dashboard YAML.
2. Extract the v0.5.4 HA drop-in archive directly into `/config`.
3. Verify all three runtime version markers report `0.5.4`.
4. Restart Home Assistant and refresh `sensor.portfolio_architect`.
5. Replace the complete dashboard raw configuration with
   `dashboard/bilingual-dashboard.yaml`.

No entity migration is required.
