# Upgrade to Portfolio Architect v1.9.0

v1.9.0 is an in-place integration and Gateway App update. It preserves the
existing Comdirect OAuth/session data, API client credentials, Gateway bearer
token, cached snapshot, Portfolio Architect config entry, live REST source, and
CSV fallback.

## 1. Update the integration

Upload `portfolio-architect-v1.9.0-ha-dropin.zip` to `/config` and run:

```bash
cd /config

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.8.0-$stamp"
archive="/config/portfolio-architect-v1.9.0-ha-dropin.zip"

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

All three version markers must report `1.9.0`.

## 2. Update the authenticated Gateway App in place

Do not uninstall the App and do not remove App data.

Upload `portfolio-architect-gateway-app-v1.9.0.zip` to `/config` and run:

```bash
ha apps stop local_portfolio_architect_gateway

archive="/config/portfolio-architect-gateway-app-v1.9.0.zip"
unzip -o "$archive" -d /addons \
  && rm -f -- "$archive"

ha store reload

ha apps info local_portfolio_architect_gateway \
  | grep -E '^(state|stage|version|version_latest):'
```

Confirm `version_latest: 1.9.0`, then run:

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
version: 1.9.0
version_latest: 1.9.0
```

No new PhotoTAN bootstrap should be required. The integration and App may be
updated in either order because health schemas 1 through 3 remain supported.
The new refresh entities become available after both components use schema 4
and the integration completes its next health fetch or is reloaded.

## 3. Dashboard update

The v1.8.0 dashboard remains functional. Replace it with the supplied v1.9.0
bilingual dashboard to add:

- next live refresh;
- refresh duration and trigger;
- a conditional live-refresh-running indicator.

After the first completed v1.9.0 refresh, verify:

```text
Gateway status: OK
Operating mode: Live
Snapshot verified: on
Next live refresh: future timestamp
Refresh duration: available
Refresh trigger: Startup, Scheduled, Manual, or Bootstrap
Live refresh running: off
Source healthy: on
Data fresh: on
Version: 1.9.0
```

## 4. Test the protected manual refresh

Open the **Portfolio Architect Gateway** App Web UI and select
**Refresh portfolio now**. The page should temporarily show the refresh as
running and then update the duration and trigger to `manual`. Home Assistant may
need one normal integration reload or polling cycle before its diagnostic tiles
show the new Gateway health values.

The action is limited to one accepted request per minute. It does not alter the
scheduled polling time, rotate credentials, change the REST endpoint, or modify
the CSV fallback.
