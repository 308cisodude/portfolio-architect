# Portfolio Architect 0.4.2 hardening upgrade

## What changes

The release corrects legacy entity IDs such as:

`sensor.portfolio_architect_portfolio_architect_world_current_allocation`

into:

`sensor.portfolio_architect_world_current_allocation`

The migration runs after the sensor platform has loaded, matches entities by
config entry and unique ID, and renames only the exact duplicated-prefix IDs.
Any entity ID renamed manually by the user is left untouched.

## Upgrade procedure

1. Back up the current dashboard YAML.
2. Replace the complete directory:

   `/config/custom_components/portfolio_architect`

   with `custom_components/portfolio_architect` from this archive.
3. Optionally replace `/config/portfolio-architect/VERSION` with the included
   `portfolio-architect/VERSION`.
4. Restart Home Assistant.
5. In **Developer Tools → States**, verify that these entities exist:

   - `sensor.portfolio_architect_world_current_allocation`
   - `sensor.portfolio_architect_world_target_allocation`

6. If the allocation dashboard shows `Entity not found`, update its entity IDs
   with this exact search-and-replace:

   - find: `sensor.portfolio_architect_portfolio_architect_`
   - replace with: `sensor.portfolio_architect_`

   Alternatively replace the current allocation stack with
   `dashboard/allocation-stack.yaml`.

Do not remove and re-add the integration. The in-place migration preserves the
entities' unique IDs and history association.

## Verification

- Force an update of `sensor.portfolio_architect`.
- Confirm both Distribution cards update without a dashboard reload.
- Confirm current allocations total approximately 100%.
- Confirm policy targets total 100%.
- Temporarily make the source sensor unavailable, if practical, and confirm the
  allocation entities become unavailable rather than retaining apparently fresh
  values.
- Download diagnostics from the Portfolio Architect integration menu and verify
  the source entity, position count, source timestamp, refresh timestamp, and
  success state are present.

Home Assistant stores the full-precision percentage state. The integration
suggests two decimal places for presentation; this avoids destructive rounding
while keeping cards readable.
