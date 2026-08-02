# Upgrade from v0.5.2 to v0.5.4

v0.5.4 removes the practical single-language dashboard limitation without
unsupported browser scripting. It adds a complete bilingual dashboard with
separate English and German views backed by the same language-neutral entities.

## Runtime upgrade

1. Back up `/config/portfolio-architect` and
   `/config/custom_components/portfolio_architect` outside `custom_components`.
2. Extract the v0.5.4 HA drop-in archive directly into `/config`.
3. Verify the engine, integration manifest, and integration constant all report
   `0.5.4`.
4. Restart Home Assistant and refresh `sensor.portfolio_architect`.

No entity IDs, calculations, schema fields, or configuration-entry migrations
change in this release.

## Dashboard upgrade

Use `dashboard/bilingual-dashboard.yaml` as the complete dashboard YAML, or add
`dashboard/en/view.yaml` and `dashboard/de/view.yaml` as two views manually.
The English view is listed first and is therefore the default view in the
reference dashboard.

Native entity states still follow each user's Home Assistant profile language.
Literal Lovelace text is localized by selecting the matching English or German
view tab. Both views use the same entities and source data.
