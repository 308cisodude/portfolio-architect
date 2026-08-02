# Upgrade to Portfolio Architect 1.13.1

Version 1.13.1 is a release-hygiene patch. It withdraws the optional Markdown
cards shipped with v1.13.0 while retaining the successful aggregate allocation
sensor and all runtime behaviour.

## 1. Dashboard action

Do not replace the existing bilingual dashboard. It remains the authoritative
native Home Assistant dashboard for Portfolio Architect.

If an optional Allocation & Drift Markdown card from v1.13.0 is still present,
delete that manual card from the English or German view. No dashboard replacement,
Home Assistant restart, or integration reconfiguration is required for this step.

## 2. Update the integration

Upload `portfolio-architect-v1.13.1-ha-dropin.zip` to `/config`, back up the current
custom component, extract the archive over `/config`, run `ha core check`, and
restart Home Assistant.

After restart, verify:

- `sensor.portfolio_architect_version` reports `1.13.1`;
- `sensor.portfolio_architect_allocation_overview` remains available;
- its state is `on_target` or `drift_detected`;
- all existing allocation, policy, source, and purchase entities retain their IDs.

There is no configuration or data migration.

## 3. Gateway App

The Gateway runtime is unchanged. The v1.13.1 App archive exists for release
parity only. Updating it in place is recommended when matching package versions
are desired, but it is not required for the v1.13.1 dashboard cleanup.

Do not uninstall the App and do not remove App data. Existing OAuth/session state,
Gateway bearer token, credentials, and cached snapshot remain intact.

## 4. Rollback

A runtime rollback is not normally useful because v1.13.1 changes no calculation
or source behaviour. If required, restore the v1.13.0 integration drop-in and
restart Home Assistant. No configuration migration needs to be reversed.
