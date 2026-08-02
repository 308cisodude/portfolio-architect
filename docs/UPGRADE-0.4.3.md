# Portfolio Architect 0.4.3 corrective migration

## Why this release exists

The v0.4.2 entity-registry migration did not rename the already registered
allocation entities on the affected installation. Version 0.4.3 no longer
reconstructs unique-ID metadata to identify them. It scans only the registry
entries owned by the Portfolio Architect config entry and renames exact legacy
IDs of this form:

`sensor.portfolio_architect_portfolio_architect_<fund>_<kind>_allocation`

into:

`sensor.portfolio_architect_<fund>_<kind>_allocation`

User-renamed IDs and already clean IDs are not changed.

## Upgrade procedure

1. Leave the currently working dashboard YAML unchanged. It should continue to
   reference the duplicated legacy IDs for now.
2. Replace the complete directory:

   `/config/custom_components/portfolio_architect`

   with `custom_components/portfolio_architect` from this archive.
3. Optionally replace `/config/portfolio-architect/VERSION` with the included
   `portfolio-architect/VERSION`.
4. Restart Home Assistant completely. Do not remove and re-add the integration.
5. Before changing the dashboard, open **Developer Tools → States** and verify
   that both clean entities exist:

   - `sensor.portfolio_architect_world_current_allocation`
   - `sensor.portfolio_architect_world_target_allocation`

6. Only after those entities exist, update the dashboard YAML:

   - find: `sensor.portfolio_architect_portfolio_architect_`
   - replace with: `sensor.portfolio_architect_`

7. Save and reload the dashboard.

If the clean entities do not exist after the restart, do not modify the
dashboard. Check the Home Assistant log for messages containing
`Portfolio Architect config-entry migration` or `Cannot migrate`.

## Verification

- The two Distribution cards render without `Entity not found`.
- The old duplicated IDs no longer appear in Developer Tools → States.
- Current allocations total approximately 100%.
- Policy targets total 100%.
- Updating `sensor.portfolio_architect` updates the allocation entities without
  reloading the dashboard.
