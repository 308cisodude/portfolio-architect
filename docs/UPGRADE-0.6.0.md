# Upgrade to v0.6.0

## Runtime files

Back up the current engine and integration outside `/config/custom_components`,
then extract the v0.6.0 drop-in archive at `/config`.

```bash
cd /config
stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v0.5.4-$stamp"
mkdir -p "$backup"
cp -a /config/portfolio-architect "$backup/portfolio-architect"
cp -a /config/custom_components/portfolio_architect "$backup/custom-component"
unzip -o /config/portfolio-architect-v0.6.0-ha-dropin.zip -d /config
```

Verify all version markers before restarting:

```bash
grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
cat /config/portfolio-architect/VERSION
```

All must report `0.6.0`.

Restart Home Assistant and refresh the source sensor:

```bash
ha core restart
```

```yaml
action: homeassistant.update_entity
target:
  entity_id: sensor.portfolio_architect
```

## Dashboard

Replace the complete dashboard raw configuration with
`dashboard/bilingual-dashboard.yaml`. The view paths and existing entity IDs are
unchanged. The monthly Markdown card is replaced by native tiles, and a compact
runtime-health row is added.

## Expected new entities

- `binary_sensor.portfolio_architect_monthly_plan_ready`
- `binary_sensor.portfolio_architect_source_healthy`
- `binary_sensor.portfolio_architect_data_fresh`
- `sensor.portfolio_architect_monthly_contribution`
- `sensor.portfolio_architect_recommended_total`
- `sensor.portfolio_architect_unallocated_contribution`
- `sensor.portfolio_architect_purchase_count`
- `sensor.portfolio_architect_<fund_id>_proposed_buy`
- `sensor.portfolio_architect_last_successful_refresh`
- `sensor.portfolio_architect_payload_schema_version`
- `sensor.portfolio_architect_version`

## Freshness option

The default freshness threshold is 24 hours. Where the integration options are
available, it can be changed from 1 to 168 hours. A source generation timestamp
more than five minutes in the future is treated as not fresh.
