# Upgrade to Portfolio Architect v1.10.2

v1.10.2 is an integration-only hotfix. Leave the stable Gateway App running on
v1.10.1.

## Install

Upload `portfolio-architect-v1.10.2-ha-dropin.zip` to `/config`, then run:

```bash
cd /config

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.10.1-$stamp"
archive="/config/portfolio-architect-v1.10.2-ha-dropin.zip"

mkdir -p -- "$backup"
cp -a /config/custom_components/portfolio_architect "$backup/custom-component"
cp -a /config/portfolio-architect "$backup/portfolio-data"

unzip -o "$archive" -d /config \
  && rm -f -- "$archive"

ha core check
ha core restart
```

Verify all three integration markers report `1.10.2`:

```bash
grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
grep -n '^__version__' /config/custom_components/portfolio_architect/engine/__init__.py
```

## Prime the corrected cache

After Home Assistant returns, leave the Gateway running and confirm one
successful live evaluation on v1.10.2. That evaluation writes the corrected
JSON-safe private cache.

Do not inspect or edit `.storage` manually.

## Repeat the outage test

Stop the Gateway:

```bash
ha apps stop local_portfolio_architect_gateway
```

Reload Portfolio Architect from **Settings → Devices & services**. Portfolio,
plan, architecture, and policy entities must remain available from the private
last-known-good cache. Runtime health should show a transport outage and
`Operating mode: Last known good`.

Restore the Gateway:

```bash
ha apps start local_portfolio_architect_gateway
```

Then reload Portfolio Architect once more.
