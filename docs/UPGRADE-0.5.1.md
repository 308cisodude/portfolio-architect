# Upgrade from v0.5.0 to v0.5.1

v0.5.1 is a presentation and internationalization refinement release. The
portfolio calculations, entity IDs, and rebalancing behavior are unchanged.

## Safe upgrade

1. Keep the v0.5.0 package as rollback material.
2. Back up `/config/custom_components/portfolio_architect` outside
   `/config/custom_components`.
3. Replace the complete custom integration directory with the v0.5.1 version.
4. Replace `/config/portfolio-architect/VERSION` and the engine package when
   using the drop-in archive, so all displayed versions remain aligned.
5. Verify before restarting:

```bash
grep -n '"version"' /config/custom_components/portfolio_architect/manifest.json
grep -n '^VERSION' /config/custom_components/portfolio_architect/const.py
cat /config/portfolio-architect/VERSION
test -f /config/custom_components/portfolio_architect/icons.json
```

All versions must report `0.5.1`, and `icons.json` must exist.

6. Restart Home Assistant Core.
7. Force a source refresh:

```yaml
action: homeassistant.update_entity
target:
  entity_id: sensor.portfolio_architect
```

No dashboard entity-ID migration is required.

## Optional language shortcut

`dashboard/language-shortcut-badge.yaml` is the recommended compact shortcut.
Add it as a view badge. It opens the official user-profile page where Home
Assistant's per-user language and locale settings are changed.

The shortcut navigates to `/profile/general`, an internal frontend route. If a
future Home Assistant release changes that route, remove the shortcut and use
the profile entry in the sidebar.
