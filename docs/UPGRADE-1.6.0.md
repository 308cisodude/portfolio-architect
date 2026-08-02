# Upgrade to Portfolio Architect v1.6.0

This release updates both the custom integration and the native Gateway App.
The authenticated Gateway App data must be preserved: update the App in place and
do not uninstall it.

## Integration

Upload `portfolio-architect-v1.6.0-ha-dropin.zip` to `/config` and run:

```bash
cd /config

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.5.1-$stamp"
archive="/config/portfolio-architect-v1.6.0-ha-dropin.zip"

mkdir -p "$backup"
cp -a /config/custom_components/portfolio_architect "$backup/custom-component"
cp -a /config/portfolio-architect "$backup/portfolio-data"

unzip -o "$archive" -d /config \
  && rm -f -- "$archive"

ha core check
ha core restart
```

## Gateway App

Upload `portfolio-architect-gateway-app-v1.6.0.zip` to `/config`, then update the
local App source while preserving its private data:

```bash
ha apps stop local_portfolio_architect_gateway

archive="/config/portfolio-architect-gateway-app-v1.6.0.zip"
unzip -o "$archive" -d /addons \
  && rm -f -- "$archive"

ha store reload
ha apps info local_portfolio_architect_gateway \
  | grep -E '^(state|version|version_latest):'
```

Do not continue until `version_latest` reports `1.6.0`. Then run:

```bash
ha apps update local_portfolio_architect_gateway
ha apps start local_portfolio_architect_gateway
ha apps logs local_portfolio_architect_gateway
```

The update preserves the successful Comdirect bootstrap, client credentials,
OAuth session, gateway bearer token, and last-known-good snapshot.
