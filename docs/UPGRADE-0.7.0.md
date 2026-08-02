# Upgrade to v0.7.0

v0.7.0 is a drop-in runtime upgrade followed by one dashboard YAML replacement.
No entity IDs from v0.6.0 are renamed.

## Back up and extract

```bash
cd /config
stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v0.6.0-$stamp"
mkdir -p "$backup"
cp -a /config/portfolio-architect "$backup/portfolio-architect"
cp -a /config/custom_components/portfolio_architect "$backup/custom-component"
unzip -o /config/portfolio-architect-v0.7.0-ha-dropin.zip -d /config
```

The drop-in archive deliberately excludes local portfolio, policy, instrument,
broker, exception, and depot data.

## Verify before restart

```bash
grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
cat /config/portfolio-architect/VERSION
```

All three values must be `0.7.0`.

## Restart and refresh

```bash
ha core restart
```

Then update `sensor.portfolio_architect` from Developer Tools.

Expected new entities include:

```text
binary_sensor.portfolio_architect_mandatory_controls_compliant
sensor.portfolio_architect_policy_status
sensor.portfolio_architect_policy_checks_evaluated
sensor.portfolio_architect_policy_error_findings
sensor.portfolio_architect_policy_warning_findings
sensor.portfolio_architect_accepted_exception_count
sensor.portfolio_architect_optimisation_opportunity_count
sensor.portfolio_architect_next_exception_review
sensor.portfolio_architect_robotics_accumulating_preferred_policy_finding
```

For the current policy, four additional savings-plan-fee opportunity sensors
are created for World, Emerging Markets, Healthcare, and Cybersecurity.

## Dashboard

Back up the dashboard raw YAML and replace it with
`dashboard/bilingual-dashboard.yaml`.
