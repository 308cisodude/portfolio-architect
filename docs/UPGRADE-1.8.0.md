# Upgrade to Portfolio Architect v1.8.0

v1.8.0 is an in-place integration and Gateway App update. It preserves the
existing Comdirect OAuth/session data, API client credentials, Gateway bearer
token, cached snapshot, Portfolio Architect config entry, and CSV fallback.

## 1. Update the integration

Upload `portfolio-architect-v1.8.0-ha-dropin.zip` to `/config` and run:

```bash
cd /config

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.7.0-$stamp"
archive="/config/portfolio-architect-v1.8.0-ha-dropin.zip"

mkdir -p -- "$backup"
cp -a /config/custom_components/portfolio_architect "$backup/custom-component"
cp -a /config/portfolio-architect "$backup/portfolio-data"

unzip -o "$archive" -d /config \
  && rm -f -- "$archive"

ha core check
ha core restart
```

Verify `1.8.0` in `manifest.json`, `const.py`, and `engine/__init__.py`.

## 2. Update the authenticated Gateway App in place

Do not uninstall the App and do not remove App data.

Upload `portfolio-architect-gateway-app-v1.8.0.zip` to `/config` and run:

```bash
ha apps stop local_portfolio_architect_gateway

archive="/config/portfolio-architect-gateway-app-v1.8.0.zip"
unzip -o "$archive" -d /addons \
  && rm -f -- "$archive"

ha store reload
ha apps update local_portfolio_architect_gateway
ha apps start local_portfolio_architect_gateway
sleep 5
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
version: 1.8.0
version_latest: 1.8.0
```

No new PhotoTAN bootstrap should be required.

The integration and App may be updated in either order. v1.8.0 requests health
schema 3; older integration clients continue to receive schemas 1 or 2.

## 3. Dashboard update

The existing v1.7.0 dashboard remains functional. Replace it with the supplied
v1.8.0 bilingual dashboard to add:

- Gateway operating mode;
- Gateway snapshot age;
- a conditional last-known-good warning.

After the first successful v1.8.0 refresh, verify:

```text
Gateway operating mode: Live
Gateway status: OK
Gateway snapshot integrity verified: on
Source healthy: on
Data fresh: on
Version: 1.8.0
```

During a transient live-refresh failure, the expected safe fallback is:

```text
Gateway operating mode: Last known good
Gateway status: Degraded
Gateway using last-known-good snapshot: on
Source healthy: off
Data fresh: on, while the accepted snapshot remains within policy
```
