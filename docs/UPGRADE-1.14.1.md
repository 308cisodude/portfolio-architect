# Upgrade to Portfolio Architect 1.14.1

Version 1.14.1 is an interaction-consistency patch for the native dashboard. It
may be installed directly over v1.14.0. Calculations, allocation corridor, source
configuration, credentials, payload schema 8, REST schema 1, Gateway health
schema 5, existing entity IDs, and last-known-good data remain compatible.

## 1. Update the integration

Upload `portfolio-architect-v1.14.1-ha-dropin.zip` to `/config`, back up the
current custom component and Portfolio Architect data directory, extract the
archive over `/config`, run `ha core check`, and restart Home Assistant.

After restart, verify that `sensor.portfolio_architect_version` reports `1.14.1`
and that this new bounded entity is available while the exception is active:

```text
sensor.portfolio_architect_robotics_accumulating_preferred_policy_exception
```

Its state is `accepted_exception`. Its bounded attributes contain only the ETF,
policy rule, observed value, expected value, decision date when present, and
review date. The long rationale remains on the original policy-finding entity and
in diagnostics.

## 2. Replace the dashboard YAML

Replace the complete raw Portfolio Architect dashboard configuration with
`portfolio-architect-v1.14.1-bilingual-dashboard.yaml`.

The compact Robotics exception tile remains half width but is clickable again.
It opens the bounded detail entity through Home Assistant's native more-info
dialog instead of the original long-attribute finding entity. No restart is
required after saving the dashboard YAML.

## 3. Gateway App

The Gateway runtime is unchanged. Its v1.14.1 archive is optional and exists for
release-version alignment. Update it only in place; do not uninstall it or remove
App data.

## 4. Rollback

Restore the v1.14.0 integration drop-in and dashboard YAML, run `ha core check`,
and restart Home Assistant. No configuration or data migration must be reversed.
