# Upgrade from v0.5.1 to v0.5.2

v0.5.2 is a visible-localization and dashboard-reference release. Runtime
entities and calculation behavior are unchanged.

## Safe upgrade

1. Keep the v0.5.1 package as rollback material.
2. Back up the engine and custom integration outside `custom_components`.
3. Extract the v0.5.2 drop-in archive directly into `/config`.
4. Verify all three version markers report `0.5.2`.
5. Restart Home Assistant Core and refresh `sensor.portfolio_architect`.

No entity-ID replacement is required.

## Dashboard language choice

Home Assistant translates entity states per user, but it does not dynamically
translate literal Lovelace YAML such as `title`, Markdown content, or table
headings. Select the dashboard variant that matches the user's preferred
language:

- `dashboard/en/` for English;
- `dashboard/de/` for German.

Replace each existing card with its matching localized YAML file. The language
shortcut badge opens `/profile/general`, where the official per-user Home
Assistant language is selected.

The root files in `dashboard/` remain English-compatible aliases so existing
v0.5.1 dashboards keep working after the code upgrade.
