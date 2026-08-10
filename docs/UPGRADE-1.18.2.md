# Upgrade to Portfolio Architect 1.18.2

Version 1.18.2 is a metadata-only compatibility correction for Home Assistant
monetary sensors. It does not change portfolio calculations or Gateway protocols.

## Home Assistant integration

Update Portfolio Architect through HACS to 1.18.2 and restart Home Assistant when
HACS requests it. Existing configuration entries, plan options, entity IDs, and
dashboard references are preserved.

After restart, verify the three integration version markers report `1.18.2` and
confirm that Home Assistant no longer logs invalid `measurement` state-class
warnings for Portfolio Architect monetary sensors.

## Gateway App

Gateway App 1.18.2 aligns package metadata only. The runtime and REST/health
contracts are unchanged from the established stable Gateway implementation.

When Home Assistant offers the App update from the Portfolio Architect Apps
repository, update it in place. Do not uninstall the App or remove its private data;
normal in-place updates preserve authentication/session state, the Gateway bearer
token, cached snapshot, and selected account.

No Comdirect reauthentication is expected solely because of this release.

## Acceptance

A successful upgrade should show:

- `sensor.portfolio_architect_version` = `1.18.2`;
- Gateway source health remains healthy/live with zero new refresh failures;
- existing portfolio and holding values remain available;
- no Portfolio Architect monetary sensor warning that says state class
  `measurement` is impossible for device class `monetary`.
