# Upgrade to v1.5.1

## Scope

v1.5.1 updates the custom integration version and adds the native Home Assistant
App deployment. It does not change config-entry schema 7, payload schema 8, REST
schema 1, entity identity, statistics metadata, policy semantics, or dashboard
YAML.

## 1. Back up and update the custom integration

```bash
cd /config

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.5.0-$stamp"

mkdir -p "$backup"
cp -a /config/custom_components/portfolio_architect \
  "$backup/custom-component"
cp -a /config/portfolio-architect \
  "$backup/portfolio-data"

unzip -o /config/portfolio-architect-v1.5.1-ha-dropin.zip -d /config

ha core check
ha core restart
```

Do not remove or re-add the integration.

Verify all version markers:

```bash
grep -n '"version"' \
  /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' \
  /config/custom_components/portfolio_architect/const.py
grep -n '^__version__' \
  /config/custom_components/portfolio_architect/engine/__init__.py
```

All must report `1.5.1`. Confirm that the existing CSV refresh remains healthy
before installing the App.

## 2. Install the local App

Extract `portfolio-architect-gateway-app-v1.5.1.zip` into `/addons`:

```bash
cd /addons
unzip -o /config/portfolio-architect-gateway-app-v1.5.1.zip

test -f /addons/portfolio_architect_gateway/config.yaml \
  && echo "Gateway App files present"
```

In Home Assistant:

1. open **Settings → Apps → App store**;
2. use the three-dot menu and select **Check for updates**;
3. install **Portfolio Architect Gateway** under **Local apps**;
4. start it and open its Web UI.

Do not enable a host mapping for port 8787.

## 3. Bootstrap and validate

Enter the Comdirect API client ID, client secret, username, and password in the
Ingress UI. Approve PhotoTAN and wait for a successful first refresh.

Record the displayed endpoint and token. Compare the gateway position count and
total against the last known-good CSV source before changing Portfolio Architect.

## 4. Switch only after comparison

Open **Portfolio Architect → Reconfigure**, select **Local REST JSON gateway**,
and enter:

```text
Endpoint: http://local-portfolio-architect-gateway:8787/api/v1/portfolio
Token:    value displayed by the Gateway App
```

The Reconfigure flow validates and calculates the complete portfolio before
committing the source change.

## Rollback

Reconfigure Portfolio Architect back to **Comdirect depot CSV**. The App can then
be stopped or uninstalled without affecting the CSV source or portfolio data
files.
