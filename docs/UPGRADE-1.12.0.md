# Upgrade to Portfolio Architect 1.12.0

Version 1.12.0 adds optional multi-source consolidation and a native DKB depot-CSV
adapter. Existing single-source configurations require no data transformation.
The config-entry schema advances automatically from 7 to 8.

## Upgrade order

1. Update the Portfolio Architect integration.
2. Update the stable Gateway App in place.
3. Replace the dashboard YAML.
4. Reload Portfolio Architect once.
5. Add the supplemental DKB export through **Configure → Portfolio sources**.

Never uninstall the Gateway App or remove its private data during a normal
upgrade. The Comdirect session, Gateway bearer token, and cached snapshot remain
in App-private storage.

## Integration update

```bash
cd /config
stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.11.0-$stamp"
archive="/config/portfolio-architect-v1.12.0-ha-dropin.zip"

mkdir -p -- "$backup"
cp -a -- /config/custom_components/portfolio_architect "$backup/custom-component"
cp -a -- /config/portfolio-architect "$backup/portfolio-data"

unzip -o "$archive" -d /config \
  && rm -f -- "$archive"

ha core check
ha core restart
```

## Gateway App update

```bash
ha apps stop local_portfolio_architect_gateway
archive="/config/portfolio-architect-gateway-app-v1.12.0.zip"

unzip -o "$archive" -d /addons \
  && rm -f -- "$archive"

ha store reload
ha apps update local_portfolio_architect_gateway
ha apps start local_portfolio_architect_gateway
```

Do not uninstall the App. PhotoTAN is required only when Comdirect rejects the
existing bank-issued session.

## Add a DKB supplemental source

Copy the DKB depot export below `/config`, for example:

```text
portfolio-sources/dkb/depot-export-31.07.2026.csv
```

Open Portfolio Architect's configuration, choose **Portfolio sources**, and enter
one relative path per line. Up to eight DKB exports are supported. The options
flow validates every file before saving and reloads the integration.

DKB market values are calculated from `Bewertungskurs × Stückzahl` using exact
decimal arithmetic. Overlapping instruments are consolidated by ISIN. Depot
numbers and performance columns are ignored.

## Verification

The healthy multi-source state shows:

```text
Portfolio sources: 2
Source provider: Multiple sources
Source conflicts: 0
Gateway status: OK
Operating mode: Live
Version: 1.12.0
Schema: 8
```

For the supplied acceptance snapshot, ISIN `IE00BJ0KDQ92` appears once with two
source contributions. The point-in-time €350 recommendation is €290 World,
€20 Cybersecurity, and €40 Robotics. Live market values can change that result.

## Rollback

Remove the DKB path through **Portfolio sources** to return to the primary source
only. The existing REST and CSV primary-source settings remain unchanged.
