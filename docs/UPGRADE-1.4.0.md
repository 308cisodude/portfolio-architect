# Upgrade to Portfolio Architect v1.4.0

v1.4.0 adds an optional local REST JSON source adapter. Existing Comdirect and
generic CSV entries remain unchanged and migrate automatically from config-entry
schema 6 to schema 7.

Payload schema 8, entity IDs, unique IDs, statistics metadata, calculations,
options, and dashboard YAML remain compatible.

## 1. Back up and install

Upload `portfolio-architect-v1.4.0-ha-dropin.zip` to `/config`, then run:

```bash
cd /config

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.3.1-$stamp"

mkdir -p "$backup"
cp -a /config/custom_components/portfolio_architect "$backup/custom-component"
cp -a /config/portfolio-architect "$backup/portfolio-data"

unzip -o /config/portfolio-architect-v1.4.0-ha-dropin.zip -d /config
```

The drop-in contains only the custom integration. It does not overwrite the CSV,
local YAML configuration, dashboard, or config-entry data.

## 2. Verify before restarting

```bash
grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
grep -n '^__version__' /config/custom_components/portfolio_architect/engine/__init__.py

ha core check
ha core restart
```

All three version markers must report `1.4.0`. Do not remove and re-add the
integration.

## 3. Validate the unchanged CSV path

For an existing Comdirect installation, use Developer Tools → Template:

```jinja
version: {{ states('sensor.portfolio_architect_version') }}
provider: {{ states('sensor.portfolio_architect_source_provider') }}
source_healthy: {{ is_state('binary_sensor.portfolio_architect_source_healthy', 'on') }}
payload_schema: {{ states('sensor.portfolio_architect_payload_schema_version') }}
```

Expected:

```text
version: 1.4.0
provider: comdirect_csv
source_healthy: True
payload_schema: 8
```

The dashboard does not need to be replaced.

## 4. Optional later switch to a local REST gateway

Do not reconfigure until a conforming gateway is deployed. Then open:

**Settings → Devices & services → Portfolio Architect → Reconfigure**

Select **Local REST JSON gateway**, retain the existing configuration directory,
and enter:

- the local HTTP(S) endpoint;
- a dedicated bearer token with no bank privileges.

The flow fetches, validates, and calculates the complete source before replacing
the existing CSV configuration. Failed validation leaves the active CSV entry
untouched.

## Rollback

Restore the backed-up custom component, run `ha core check`, and restart Home
Assistant. A CSV entry requires no data rollback. Do not switch a REST-configured
entry back to v1.3.1 without first reconfiguring it to CSV, because v1.3.1 does
not understand config-entry schema 7 or the REST adapter.
