# Upgrade to Portfolio Architect v1.1.1

This maintenance release corrects the Home Assistant integration classification and prevents duplicate config entries.

## Fixed

- `integration_type` is now `service`, so Portfolio Architect appears under Integrations rather than Helpers.
- `single_config_entry` prevents a second Portfolio Architect instance from being added accidentally.
- The config-entry unique ID is stable and no longer derived from mutable file paths.
- Reconfigure updates source paths on the existing entry.

## Existing duplicate entries

Home Assistant does not silently choose which duplicate source to keep. Install v1.1.1, restart, remove all Portfolio Architect entries in the UI, and add the integration once with the intended source. Do not edit `.storage`.
