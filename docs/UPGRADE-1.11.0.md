# Upgrade to Portfolio Architect v1.11.0

v1.11.0 is a compatible publication-readiness release. It preserves config-entry
schema 7, payload schema 8, REST portfolio schema 1, Gateway health schema 5,
the REST endpoint, bearer token, calculation and policy logic, existing entity
IDs, and the Home Assistant-side last-known-good cache.

## 1. Update the integration

Upload `portfolio-architect-v1.11.0-ha-dropin.zip` to `/config`, then run:

```bash
cd /config

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.10.2-$stamp"
archive="/config/portfolio-architect-v1.11.0-ha-dropin.zip"

mkdir -p -- "$backup"
cp -a -- /config/custom_components/portfolio_architect "$backup/custom-component"
cp -a -- /config/portfolio-architect "$backup/portfolio-data"

unzip -o "$archive" -d /config \
  && rm -f -- "$archive"

grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
grep -n '^__version__' /config/custom_components/portfolio_architect/engine/__init__.py

ha core check
ha core restart
```

All three version markers must report `1.11.0`. After Home Assistant returns,
confirm that the live or last-known-good portfolio remains available.

## 2. Update the Gateway App in place

Do not uninstall the App and do not remove its private data. Upload
`portfolio-architect-gateway-app-v1.11.0.zip` to `/config`, then run:

```bash
ha apps stop local_portfolio_architect_gateway

archive="/config/portfolio-architect-gateway-app-v1.11.0.zip"
unzip -o "$archive" -d /addons \
  && rm -f -- "$archive"

ha store reload
ha apps info local_portfolio_architect_gateway \
  | grep -E '^(state|stage|version|version_latest):'
```

Proceed only when `version_latest: 1.11.0` is visible:

```bash
ha apps update local_portfolio_architect_gateway
ha apps start local_portfolio_architect_gateway
sleep 5

ha apps info local_portfolio_architect_gateway \
  | grep -E '^(state|stage|version|version_latest):'

ha apps logs local_portfolio_architect_gateway \
  | tail -30
```

Expected final state:

```text
stage: stable
state: started
version: 1.11.0
version_latest: 1.11.0
```

The existing Comdirect session, Gateway bearer token and cached snapshot are
preserved. A new PhotoTAN is required only if Comdirect genuinely rejects the
bank-issued session.

## 3. Replace the dashboard YAML

Replace the dashboard raw YAML with
`portfolio-architect-v1.11.0-bilingual-dashboard.yaml`.

The new **Refresh schedule** card displays two pieces of information:

- a translated state: `Scheduled`, `Due now`, `Overdue`, or `Refreshing`;
- the scheduled timestamp rendered as a relative time.

The existing diagnostic timestamp entity is retained and renamed **Scheduled
refresh time**. No existing entity is removed.

## 4. Verify

Reload Portfolio Architect once after both components are updated:

**Settings → Devices & services → Portfolio Architect → ⋮ → Reload**

Expected healthy state:

```text
Source healthy
Data fresh
Gateway status: OK
Operating mode: Live
Snapshot verified
Refresh schedule: Scheduled
Version: 1.11.0
Schema: 8
```

The complete source archive also contains release-building, verification,
backup, rollback and retention tools. These tools are not copied by the
integration drop-in and do not alter the running installation automatically.
