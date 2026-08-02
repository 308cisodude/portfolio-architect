# Upgrade to Portfolio Architect 1.12.1

Version 1.12.1 is a presentation and observability hotfix for v1.12.0. It adds
compact regional refresh timestamps, synchronized recovery guidance, and visible
per-position source provenance. Portfolio calculations and source configuration do
not change.

## 1. Update the Home Assistant integration

Upload `portfolio-architect-v1.12.1-ha-dropin.zip` to `/config`, then run:

```bash
cd /config

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.12.0-$stamp"
archive="/config/portfolio-architect-v1.12.1-ha-dropin.zip"

mkdir -p -- "$backup"
cp -a -- /config/custom_components/portfolio_architect "$backup/custom-component"
cp -a -- /config/portfolio-architect "$backup/portfolio-data"

unzip -o "$archive" -d /config \
  && rm -f -- "$archive"

ha core check
ha core restart
```

After Home Assistant returns, the integration, engine, and manifest version must
all report `1.12.1`.

## 2. Gateway App update is optional

The Gateway runtime is unchanged and the v1.12.0 App remains fully compatible.
Skipping this step avoids an unnecessary Gateway restart. Update only when you want
release-version parity. Do not uninstall the App and do not remove its private data.

```bash
ha apps stop local_portfolio_architect_gateway

archive="/config/portfolio-architect-gateway-app-v1.12.1.zip"
unzip -o "$archive" -d /addons \
  && rm -f -- "$archive"

ha store reload
ha apps update local_portfolio_architect_gateway
ha apps start local_portfolio_architect_gateway
```

Verify `stage: stable`, `state: started`, and version `1.12.1`. Existing OAuth
state, Gateway bearer token, and cached snapshot remain in App-private storage.

## 3. Replace the dashboard YAML

Replace the dashboard raw configuration with
`portfolio-architect-v1.12.1-bilingual-dashboard.yaml`.

The runtime section now shows one state-specific refresh tile. Its timestamp is
formatted from the native timestamp entity using the user's Home Assistant regional
settings. The target architecture shows a source-contribution tile only for target
positions held across more than one configured source.

## 4. Verify

Expected healthy runtime state:

```text
Source healthy
Data fresh
Gateway status: OK
Operating mode: Live
Refresh scheduled: compact regional date/time
Snapshot verified
Version: 1.12.1
Schema: 8
```

For the live-tested overlapping MSCI World position, the target architecture should
show a card similar to:

```text
MSCI World sources
Comdirect … EUR · DKB 1 273.36 EUR
```

The exact Comdirect contribution follows the current live valuation.
