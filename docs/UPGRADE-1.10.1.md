# Upgrade to Portfolio Architect v1.10.1

v1.10.1 is an in-place integration and Gateway App hotfix. It preserves the
existing config entry, REST endpoint, Gateway bearer token, App-private
credentials/session material, cached Gateway snapshot, entity IDs, dashboard,
and CSV fallback.

## 1. Update the integration

Upload `portfolio-architect-v1.10.1-ha-dropin.zip` to `/config`, then run:

```bash
cd /config

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.10.0-$stamp"
archive="/config/portfolio-architect-v1.10.1-ha-dropin.zip"

mkdir -p -- "$backup"
cp -a /config/custom_components/portfolio_architect "$backup/custom-component"
cp -a /config/portfolio-architect "$backup/portfolio-data"

unzip -o "$archive" -d /config \
  && rm -f -- "$archive"

ha core check
ha core restart
```

Verify all three version markers report `1.10.1`.

Allow one successful live Portfolio Architect evaluation before running the
outage drill. That evaluation creates the Home Assistant-private last-known-good
cache.

## 2. Update the Gateway App in place

Do not uninstall the App and do not remove its data.

Upload `portfolio-architect-gateway-app-v1.10.1.zip` to `/config`, then run:

```bash
ha apps stop local_portfolio_architect_gateway

archive="/config/portfolio-architect-gateway-app-v1.10.1.zip"
unzip -o "$archive" -d /addons \
  && rm -f -- "$archive"

ha store reload
ha apps update local_portfolio_architect_gateway
ha apps start local_portfolio_architect_gateway
sleep 5

ha apps info local_portfolio_architect_gateway \
  | grep -E '^(state|stage|version|version_latest):'
```

Expected final state:

```text
stage: stable
state: started
version: 1.10.1
version_latest: 1.10.1
```

An in-place update normally preserves the current session. A later or prolonged
App stop can still require PhotoTAN if Comdirect's refresh session genuinely
expires during downtime.

## 3. Repeat the focused resilience tests

After one successful live refresh has seeded the Home Assistant cache:

1. Stop the Gateway App and reload Portfolio Architect. Calculated entities must
   remain available while runtime health reports last-known-good operation and
   connectivity attention.
2. Start the Gateway App again. Live operation should resume when the bank
   session remains valid; genuine expiry may require PhotoTAN.
3. Leave the Gateway Web UI open during successful PhotoTAN recovery. Gateway
   status and operating mode must turn green automatically without reloading the
   page.
