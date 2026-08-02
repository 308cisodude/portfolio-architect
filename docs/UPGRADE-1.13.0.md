# Upgrade to Portfolio Architect 1.13.0

Version 1.13.0 introduced one aggregate allocation entity. Portfolio calculations,
source adapters, configuration, credentials, entity IDs, payload schema 8, REST
schema 1, and the last-known-good cache remained unchanged.

> **Presentation withdrawal:** The optional Markdown presentation originally
> published beside v1.13.0 was withdrawn in v1.13.1 after live evaluation showed
> that it duplicated the existing native dashboard. Keep the native bilingual
> dashboard and remove the manual Markdown card if it was added.

## 1. Back up

Create a Home Assistant backup before replacing the custom integration. Keep the
working v1.12.2 archives and their recorded SHA-256 hashes as the rollback baseline.

## 2. Update the integration

Upload `portfolio-architect-v1.13.0-ha-dropin.zip` to `/config`, then extract it so
that the archive's `custom_components/portfolio_architect` directory replaces the
existing directory. Run a Home Assistant configuration check and restart Home
Assistant.

After restart, verify:

- `sensor.portfolio_architect_version` reports `1.13.0`;
- `sensor.portfolio_architect_allocation_overview` is available;
- its state is `on_target` or `drift_detected`;
- its attributes contain `underweight`, `on_target`, and `overweight` lists;
- existing allocation, policy, source, and purchase entities retain their IDs.

## 3. Update the Gateway App

The Gateway runtime is unchanged, but the v1.13.0 App archive aligns package
metadata and corrects the Dockerfile's default build label. Update the App in place.
Do not uninstall it and do not remove App data. Existing OAuth/session state,
Gateway bearer token, credentials, and cached snapshot remain intact.

## 4. Dashboard

Keep the existing bilingual native dashboard unchanged. The aggregate sensor is
available for templates, automations, diagnostics, and future native presentation,
but it does not require an additional dashboard card.

## 5. Rollback

If validation fails, restore the v1.12.2 integration drop-in and restart Home
Assistant. The aggregate entity will disappear; no configuration or data migration
needs to be reversed.
