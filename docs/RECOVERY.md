# Recovery runbook

## Portfolio entities unavailable

1. Open `binary_sensor.portfolio_architect_source_healthy`.
2. Read its `last_error`, `source`, and `configuration_directory` attributes.
3. Confirm the CSV and the required YAML files exist at those relative paths.
4. Use **Settings → Devices & services → Portfolio Architect → Reconfigure** to
   correct a path.
5. Update `binary_sensor.portfolio_architect_source_healthy` or reload the
   integration after correcting the source.

## Automatic v1.1 migration retained legacy mode

This means the default local files were missing or invalid during upgrade. Keep
the old command-line sensor temporarily, use **Reconfigure** to select valid
local files, and confirm `source_type: local_files` before cleanup.

## Device page shows an old version

```bash
grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
grep -n '^__version__' /config/custom_components/portfolio_architect/engine/__init__.py
```

## Import error mentioning a backup directory

Move every backup out of `/config/custom_components`. Home Assistant treats each
first-level directory there as a custom integration domain.

## Distribution cards show Entity not found

Use clean entity IDs with one prefix only:

`sensor.portfolio_architect_<fund>_<current|target>_allocation`

## Gateway App unreachable on v1.10.2 or later

After at least one successful live REST evaluation on v1.10.2, Portfolio
Architect keeps the most recent validated calculation in Home Assistant private
storage. During a complete Gateway outage, the calculation entities remain
available while runtime health reports:

- source unhealthy;
- operating mode `last_known_good`;
- Gateway attention required;
- recommended action `check_connectivity`.

The cache is not a live refresh and its data freshness continues to age from the
original snapshot timestamp. Restart the Gateway App and reload Portfolio
Architect after connectivity returns.

## Gateway requests PhotoTAN after restart

A prolonged App stop can allow the bank-issued refresh session to expire. Open
the protected Portfolio Architect Gateway — Comdirect Ingress page and complete the PhotoTAN
bootstrap again. Do not uninstall the App, remove its data, regenerate the
Gateway bearer token, or reconfigure the Home Assistant integration.

The page should change from amber to green automatically after successful
reauthentication. If Home Assistant still shows the prior state, reload the
Portfolio Architect integration once.
