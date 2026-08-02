# Upgrade to Portfolio Architect 1.14.0

Version 1.14.0 is a native-dashboard refinement release. It also contains the
v1.13.1 release-hygiene cleanup, so upgrading directly from an installed v1.13.0
is supported. No intermediate v1.13.1 deployment is required.

## 1. Update the integration

Upload `portfolio-architect-v1.14.0-ha-dropin.zip` to `/config`, back up the
current custom component and Portfolio Architect data directory, extract the
archive over `/config`, run `ha core check`, and restart Home Assistant.

After restart, verify:

- `sensor.portfolio_architect_version` reports `1.14.0`;
- `sensor.portfolio_architect_allocation_overview` remains available;
- all existing allocation, policy, source, purchase, and runtime entities retain
  their IDs;
- live or last-known-good operation remains healthy.

There is no configuration, payload, source, credential, or cache migration.

## 2. Replace the dashboard YAML

Replace the complete raw Portfolio Architect dashboard configuration with
`portfolio-architect-v1.14.0-bilingual-dashboard.yaml`.

This dashboard update:

- keeps both existing English and German native Sections views;
- compacts the accepted Robotics exception tile to half width;
- prevents that tile from opening the unwieldy long-attribute dialog;
- leaves every other dashboard section and entity contract intact;
- contains no Markdown or custom card.

The exception details remain present in the entity attributes and diagnostics;
the reference dashboard intentionally presents only the bounded operational
summary, review date, and decision date.

No Home Assistant restart is required after replacing the dashboard YAML.

## 3. Gateway App

The Gateway runtime is unchanged. The v1.14.0 App archive exists for release
parity only. Updating it in place is optional but keeps package versions aligned.

Do not uninstall the App and do not remove App data. Existing OAuth/session state,
Gateway bearer token, credentials, and cached snapshot remain intact.

## 4. Rollback

Restore the v1.13.0 integration drop-in and the previously saved dashboard YAML,
then run `ha core check` and restart Home Assistant. No configuration or data
migration needs to be reversed.
