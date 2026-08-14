# Upgrade to Portfolio Architect 1.26.5

Version 1.26.5 is a presentation hotfix for the remaining date-only Tile issue found
during v1.26.4 live acceptance. It does not change portfolio calculation, provider
acquisition, source atomicity, identity matching, authorized cash, or any Gateway
wire schema.

## What changes

The five existing `sensor.portfolio_architect_*` DATE sensors remain unchanged and
continue to be the authoritative values. Version 1.26.5 adds five read-only
`date.portfolio_architect_*` counterparts solely because Home Assistant's frontend
locale-formats the native `date` domain but currently renders a `sensor` with device
class `date` as its raw ISO state in a Tile.

The new date entities mirror the original Python `date` values exactly. There is no
fake noon timestamp, timezone conversion, template formatting, or hard-coded locale
pattern. Writes through `date.set_value` are rejected.

## Upgrade

1. Update **Portfolio Architect Gateway — Comdirect** to 1.26.5 in place.
2. Update **Portfolio Architect Gateway — Trade Republic** to 1.26.5 in place.
3. If installed, update **Portfolio Architect Gateway — DKB** to 1.26.5 in place;
   it remains an experimental manual-only non-live shell.
4. Update Portfolio Architect to 1.26.5 through HACS.
5. Restart Home Assistant once after the HACS update.
6. Do not reauthenticate Comdirect, re-enter Gateway tokens, re-import the Trade
   Republic statement, or recreate the Portfolio Architect configuration solely for
   this release.

## Existing copied dashboard

HACS does not overwrite a copied/imported Lovelace dashboard. Deliberately update
your copied dashboard from the v1.26.5 reference YAML to use the new `date.*`
presentation entities.

The dashboard conditions continue to use the original sensors. Only the visible
entity of the affected date Tiles changes. Those Tiles deliberately route `more-info` to the original authoritative sensor
because Home Assistant's native `date` more-info dialog is an editor, while these
mirrors are read-only.

## Live acceptance

A successful v1.26.5 acceptance should show:

1. The healthy portfolio remains 3 sources / 3 providers / 7 of 7 and all accepted
   v1.26.3/v1.26.4 policy/outage behavior remains unchanged.
2. Developer Tools → States still shows the authoritative
   `sensor.portfolio_architect_planned_execution`, `next_plan_review`,
   `last_exception_decision`, `next_exception_review`, and
   `oldest_overdue_exception_review` states as native ISO dates when available.
3. The corresponding visible reference-dashboard Tiles render in Home Assistant's
   normal locale date style rather than raw `YYYY-MM-DD`.
4. The new `date.portfolio_architect_*` presentation entities expose the same dates
   as their sensor counterparts.
5. Refresh-schedule timestamp Tiles remain in their existing localized date/time
   style and do not gain seconds-specific formatting.
6. No Comdirect reauthentication, Gateway reconfiguration, or Trade Republic
   statement re-import is required.

## Compatibility

- payload schema: 8 (unchanged)
- REST portfolio schema: 1 (unchanged)
- Gateway health schema: 6 (unchanged)
- existing Home Assistant entity IDs / unique IDs: unchanged
- five additive read-only `date.*` presentation entities
- existing machine-readable sensor states and availability semantics: unchanged
- no trading, order, transfer, payment or transaction-history capability
