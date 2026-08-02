# Upgrade to Portfolio Architect v1.7.0

v1.7.0 is an in-place integration and Gateway App update. It preserves the
existing Comdirect OAuth/session data, Gateway bearer token, cached snapshot,
Portfolio Architect config entry, and CSV fallback.

## 1. Update the integration

Upload `portfolio-architect-v1.7.0-ha-dropin.zip` to `/config` and run:

```bash
cd /config

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.6.1-$stamp"
archive="/config/portfolio-architect-v1.7.0-ha-dropin.zip"

mkdir -p -- "$backup"
cp -a /config/custom_components/portfolio_architect "$backup/custom-component"
cp -a /config/portfolio-architect "$backup/portfolio-data"

unzip -o "$archive" -d /config \
  && rm -f -- "$archive"

ha core check
ha core restart
```

Verify `1.7.0` in `manifest.json`, `const.py`, and `engine/__init__.py`.

## 2. Update the authenticated Gateway App in place

Do not uninstall the App and do not remove App data.

Upload `portfolio-architect-gateway-app-v1.7.0.zip` to `/config` and run:

```bash
ha apps stop local_portfolio_architect_gateway

archive="/config/portfolio-architect-gateway-app-v1.7.0.zip"
unzip -o "$archive" -d /addons \
  && rm -f -- "$archive"

ha store reload
ha apps update local_portfolio_architect_gateway
ha apps start local_portfolio_architect_gateway
```

Verify:

```bash
ha apps info local_portfolio_architect_gateway \
  | grep -E '^(state|stage|version|version_latest):'
```

Expected values:

```text
stage: stable
state: started
version: 1.7.0
version_latest: 1.7.0
```

No new PhotoTAN bootstrap should be required.

The integration and App may be updated in either order. v1.7.0 explicitly
requests health schema 2; older integration clients continue to receive the
original health document.

## 3. Dashboard update

The existing dashboard remains functional. Replace it with the supplied v1.7.0
bilingual dashboard only to add the new `Snapshot verified` and `Snapshot
generated` tiles.

After one successful refresh, verify:

```text
Gateway snapshot integrity verified: on
Gateway snapshot generated: recent timestamp
Gateway status: OK
Source healthy: on
Data fresh: on
```

The integrity entity may briefly be unavailable between the integration and App
updates. It becomes available after the first v1.7.0 Gateway response.
