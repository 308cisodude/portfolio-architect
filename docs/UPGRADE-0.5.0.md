# Upgrade from v0.4.3 to v0.5.0

## Safe upgrade sequence

1. Keep the v0.4.3 stable archive as the rollback package.
2. Back up these directories outside `custom_components`:

```text
/config/portfolio-architect
/config/custom_components/portfolio_architect
```

3. Replace the engine runtime package:

```text
/config/portfolio-architect/portfolio_architect
/config/portfolio-architect/VERSION
```

Do not overwrite `portfolio.yaml`, `policy.yaml`, `instruments.yaml`,
`broker.yaml`, or `exceptions.yaml` unless intentionally adopting the supplied
reference configuration.

4. Replace the complete integration directory:

```text
/config/custom_components/portfolio_architect
```

5. Verify before restarting:

```bash
grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
cat /config/portfolio-architect/VERSION
```

All three checks must report `0.5.0`.

6. Restart Home Assistant Core.
7. Force a source refresh:

```yaml
action: homeassistant.update_entity
target:
  entity_id: sensor.portfolio_architect
```

8. Verify the new entities:

```text
sensor.portfolio_architect_target_position_coverage
binary_sensor.portfolio_architect_target_architecture_complete
binary_sensor.portfolio_architect_robotics_target_position_held
```

For the 6-of-7 test portfolio, expected states are approximately:

```text
85.71%
incomplete / off
missing / off
```

9. Add `dashboard/target-architecture.yaml` as a new full-width card. Existing
allocation, monthly-plan, and compliance cards remain compatible.

## Drop-in archive

The separate HA drop-in archive contains only runtime files and can be safely
extracted into `/config`; it does not overwrite portfolio or policy YAML files.
