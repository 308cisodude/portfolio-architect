# Upgrade to Portfolio Architect v1.3.0

v1.3.0 introduces explicit Comdirect and generic CSV adapters while preserving
payload schema 8 and all existing calculations.

## 1. Back up and install

Upload `portfolio-architect-v1.3.0-ha-dropin.zip` to `/config`, then run:

```bash
cd /config

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.2.0-$stamp"

mkdir -p "$backup"
cp -a /config/custom_components/portfolio_architect "$backup/custom-component"
cp -a /config/portfolio-architect "$backup/portfolio-data"

unzip -o /config/portfolio-architect-v1.3.0-ha-dropin.zip -d /config
```

The drop-in contains only the custom integration. It does not overwrite the CSV
or local portfolio configuration.

## 2. Verify before restarting

```bash
echo '--- manifest ---'
grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json

echo '--- integration constant ---'
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py

echo '--- engine version ---'
grep -n '^__version__' /config/custom_components/portfolio_architect/engine/__init__.py
```

All three values must report `1.3.0`.

Then run:

```bash
ha core check
ha core restart
```

Do not remove or re-add the integration. The existing v1.2 config entry migrates
in place to the explicit **Comdirect depot CSV** adapter.

## 3. Verify the migrated provider

Use Developer Tools → Template:

```jinja
version:
  {{ states('sensor.portfolio_architect_version') }}

source_provider:
  {{ states('sensor.portfolio_architect_source_provider') }}

source_healthy:
  {{ states('binary_sensor.portfolio_architect_source_healthy') }}

source:
  {{ state_attr('binary_sensor.portfolio_architect_source_healthy', 'source') }}
```

Expected for the current installation:

```text
version: 1.3.0
source_provider: comdirect_csv
source_healthy: on
source: portfolio-architect/depot.csv
```

## 4. Dashboard

The v1.2 dashboard remains compatible. Replacing the complete raw dashboard with
the v1.3 bilingual dashboard adds a native **CSV provider / CSV-Anbieter** tile.

## 5. Optional generic CSV

To test another bank/export format:

1. retain the current Comdirect CSV backup;
2. open **Portfolio Architect → Reconfigure**;
3. select **Generic mapped CSV**;
4. choose encoding, delimiter, header row, and number format;
5. map identifier, name, market value, and optional metadata columns;
6. submit only after the previewed header is correct.

Portfolio Architect validates the complete portfolio calculation before saving
the new source. Market values must already be in EUR.

## Rollback

Restore the backed-up custom component, run `ha core check`, and restart Home
Assistant. A v1.2 component ignores the additive provider data only after its
config entry has been restored from the backup; do not edit `.storage` manually.
