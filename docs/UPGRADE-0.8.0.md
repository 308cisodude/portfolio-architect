# Upgrade to v0.8.0

v0.8.0 is a drop-in runtime upgrade followed by one dashboard YAML replacement.
No existing entity IDs are renamed.

## Back up and extract

```bash
cd /config
stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v0.7.0-$stamp"
mkdir -p "$backup"
cp -a /config/portfolio-architect "$backup/portfolio-architect"
cp -a /config/custom_components/portfolio_architect "$backup/custom-component"
unzip -o /config/portfolio-architect-v0.8.0-ha-dropin.zip -d /config
```

The drop-in archive excludes local portfolio, policy, instrument, broker,
exception, and depot data.

## Verify before restart

```bash
grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
cat /config/portfolio-architect/VERSION
```

All three values must be `0.8.0`.

## Restart and refresh

```bash
ha core restart
```

Then update `sensor.portfolio_architect` from Developer Tools.

Expected new entities include:

```text
binary_sensor.portfolio_architect_portfolio_allocation_on_target
sensor.portfolio_architect_portfolio_value
sensor.portfolio_architect_allocation_corridor
sensor.portfolio_architect_underweight_position_count
sensor.portfolio_architect_on_target_position_count
sensor.portfolio_architect_overweight_position_count
sensor.portfolio_architect_world_allocation_status
sensor.portfolio_architect_world_allocation_drift
sensor.portfolio_architect_world_allocation_value_gap
binary_sensor.portfolio_architect_exception_review_overdue
sensor.portfolio_architect_overdue_exception_review_count
sensor.portfolio_architect_oldest_overdue_exception_review
sensor.portfolio_architect_last_exception_decision
```

Equivalent per-position allocation entities are created for every configured
portfolio position.

## Dashboard

Back up the dashboard raw YAML and replace it with
`dashboard/bilingual-dashboard.yaml`.
