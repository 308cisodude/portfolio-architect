# Upgrade to Portfolio Architect v1.3.1

v1.3.1 is a focused Home Assistant statistics-compatibility patch. It restores
`measurement` state classes for the established contribution and proposed-buy
entities that previously generated long-term statistics.

No entity ID, unique ID, payload field, source-provider setting, calculation, or
configuration schema changes.

## 1. Back up and install

Upload `portfolio-architect-v1.3.1-ha-dropin.zip` to `/config`, then run:

```bash
cd /config

stamp="$(date +%Y%m%d-%H%M%S)"
backup="/config/portfolio-architect-backups/v1.3.0-$stamp"

mkdir -p "$backup"
cp -a /config/custom_components/portfolio_architect "$backup/custom-component"
cp -a /config/portfolio-architect "$backup/portfolio-data"

unzip -o /config/portfolio-architect-v1.3.1-ha-dropin.zip -d /config
```

The drop-in contains only the custom integration. It does not overwrite the CSV
or local portfolio configuration.

## 2. Verify before restarting

```bash
echo '--- manifest ---'
grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json

echo '--- integration constant ---'
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py

echo '--- engine version ---'
grep -n '^__version__' /config/custom_components/portfolio_architect/engine/__init__.py
```

All three values must report `1.3.1`.

Then run:

```bash
ha core check
ha core restart
```

Do not remove or re-add the integration.

## 3. Validate the patch

Use Developer Tools → Template:

```jinja
version:
  {{ states('sensor.portfolio_architect_version') }}

monthly_contribution_state_class:
  {{ state_attr('sensor.portfolio_architect_monthly_contribution', 'state_class') }}

recommended_total_state_class:
  {{ state_attr('sensor.portfolio_architect_recommended_total', 'state_class') }}

unallocated_contribution_state_class:
  {{ state_attr('sensor.portfolio_architect_unallocated_contribution', 'state_class') }}

world_proposed_buy_state_class:
  {{ state_attr('sensor.portfolio_architect_world_proposed_buy', 'state_class') }}
```

Expected:

```text
version: 1.3.1
monthly_contribution_state_class: measurement
recommended_total_state_class: measurement
unallocated_contribution_state_class: measurement
world_proposed_buy_state_class: measurement
```

The same `measurement` state class applies to every active
`*_proposed_buy` entity.

## 4. Home Assistant Repairs

After Recorder has processed the new entity metadata, the existing
**The entity no longer has a state class** repair items should clear. Do not
delete their historical statistics before testing v1.3.1; the purpose of this
patch is to preserve them.

If a repair remains after one additional restart, open that repair and verify
that it references one of the active Portfolio Architect entities above rather
than an entity that has genuinely been removed.

## Rollback

Restore the backed-up custom component, run `ha core check`, and restart Home
Assistant. No config-entry rollback is required because v1.3.1 does not change
entry data or options.
