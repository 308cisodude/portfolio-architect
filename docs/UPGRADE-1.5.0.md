# Upgrade to Portfolio Architect v1.5.0

v1.5.0 supplies the dedicated Comdirect read-only gateway that the v1.4.0 local
REST adapter was designed to consume. The gateway remains a separate service;
bank authentication is not moved into Home Assistant.

Payload schema 8, REST source schema 1, config-entry schema 7, entity IDs,
statistics metadata, plan/policy semantics, and dashboard YAML remain compatible.
The active CSV source is not changed automatically.

## 1. Back up and install the Home Assistant component

Upload `portfolio-architect-v1.5.0-ha-dropin.zip` to `/config`, then run:

```bash
cd /config

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.4.0-$stamp"

mkdir -p "$backup"
cp -a /config/custom_components/portfolio_architect "$backup/custom-component"
cp -a /config/portfolio-architect "$backup/portfolio-data"

unzip -o /config/portfolio-architect-v1.5.0-ha-dropin.zip -d /config

grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
grep -n '^__version__' /config/custom_components/portfolio_architect/engine/__init__.py

ha core check
ha core restart
```

All three version markers must report `1.5.0`. Do not remove and re-add the
integration.

## 2. Verify the unchanged source first

```jinja
version: {{ states('sensor.portfolio_architect_version') }}
provider: {{ states('sensor.portfolio_architect_source_provider') }}
source_healthy: {{ is_state('binary_sensor.portfolio_architect_source_healthy', 'on') }}
payload_schema: {{ states('sensor.portfolio_architect_payload_schema_version') }}
```

Expected before the deliberate source switch:

```text
version: 1.5.0
provider: comdirect_csv
source_healthy: True
payload_schema: 8
```

The dashboard does not need to be replaced.

## 3. Deploy the separate gateway

Use `portfolio-architect-gateway-v1.5.0.zip` and follow
`gateway/README.md`. The reference Docker Compose deployment:

- pins the runtime image by digest;
- runs as non-root with a read-only root filesystem;
- drops every Linux capability and enables `no-new-privileges`;
- mounts username/password only into the one-shot bootstrap container;
- exposes no inbound trading operation;
- publishes on loopback unless one explicit host address is configured.

Do not switch Portfolio Architect away from CSV until the bootstrap has produced
a valid authenticated response at:

```text
http://GATEWAY_IP:8787/api/v1/portfolio
```

## 4. Switch to REST after the live checkpoint

Open:

**Settings → Devices & services → Portfolio Architect → Reconfigure**

Choose **Local REST JSON gateway**, retain the existing configuration directory,
and enter the gateway endpoint and its dedicated local bearer token. The flow
fetches, validates, and calculates the complete source before committing the new
configuration.

After reload, verify:

```jinja
version: {{ states('sensor.portfolio_architect_version') }}
provider: {{ states('sensor.portfolio_architect_source_provider') }}
source_healthy: {{ is_state('binary_sensor.portfolio_architect_source_healthy', 'on') }}
data_fresh: {{ is_state('binary_sensor.portfolio_architect_data_fresh', 'on') }}
payload_schema: {{ states('sensor.portfolio_architect_payload_schema_version') }}
```

Expected:

```text
version: 1.5.0
provider: local_rest_json
source_healthy: True
data_fresh: True
payload_schema: 8
```

Compare total portfolio value and holding count with the last CSV import before
retiring the manual export workflow.

## Rollback

The gateway and Home Assistant component are independently reversible.

- To restore the source, Reconfigure Portfolio Architect back to **Comdirect depot
  CSV** and enter the preserved CSV path.
- To restore the component, copy back the v1.4.0 custom-component backup, run
  `ha core check`, and restart Home Assistant.
- Stop the gateway with `docker compose down`; do not delete the session file
  until rollback is complete.
