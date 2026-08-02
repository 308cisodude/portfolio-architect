# Upgrade to Portfolio Architect v1.10.0

v1.10.0 is an in-place integration and Gateway App update. It preserves the
Comdirect OAuth/session state, API client credentials, Gateway bearer token,
cached snapshot, Portfolio Architect config entry, live REST source, and CSV
fallback.

## 1. Update the integration

Upload `portfolio-architect-v1.10.0-ha-dropin.zip` to `/config` and run:

```bash
cd /config

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.9.0-$stamp"
archive="/config/portfolio-architect-v1.10.0-ha-dropin.zip"

mkdir -p -- "$backup"
cp -a /config/custom_components/portfolio_architect "$backup/custom-component"
cp -a /config/portfolio-architect "$backup/portfolio-data"

unzip -o "$archive" -d /config \
  && rm -f -- "$archive"

grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
grep -n '^__version__' /config/custom_components/portfolio_architect/engine/__init__.py

ha core check
ha core restart
```

All three version markers must report `1.10.0`.

## 2. Update the authenticated Gateway App in place

Do not uninstall the App and do not remove App data.

Upload `portfolio-architect-gateway-app-v1.10.0.zip` to `/config` and run:

```bash
ha apps stop local_portfolio_architect_gateway

archive="/config/portfolio-architect-gateway-app-v1.10.0.zip"
unzip -o "$archive" -d /addons \
  && rm -f -- "$archive"

ha store reload

ha apps info local_portfolio_architect_gateway \
  | grep -E '^(state|stage|version|version_latest):'
```

Confirm `version_latest: 1.10.0`, then run:

```bash
ha apps update local_portfolio_architect_gateway
ha apps start local_portfolio_architect_gateway
sleep 5

ha apps info local_portfolio_architect_gateway \
  | grep -E '^(state|stage|version|version_latest):'

ha apps logs local_portfolio_architect_gateway \
  | tail -30
```

Expected values:

```text
stage: stable
state: started
version: 1.10.0
version_latest: 1.10.0
```

No PhotoTAN bootstrap should be required. Either component may be updated first
because Gateway health schemas 1 through 4 remain supported during the rolling
upgrade.

## 3. Dashboard and health negotiation

The v1.9.0 dashboard remains functional. Replace it with the supplied v1.10.0
bilingual dashboard to add conditional attention and recovery cards.

After both components are updated, reload Portfolio Architect once:

**Settings → Devices & services → Portfolio Architect → ⋮ → Reload**

Expected healthy state:

```text
Gateway attention required: off
Attention reason: None
Recommended action: None
Live refresh overdue: off
Gateway status: OK
Operating mode: Live
Snapshot verified: on
Source healthy: on
Data fresh: on
Version: 1.10.0
Schema: 8
```

The conditional recovery cards remain hidden while the live source is healthy.
