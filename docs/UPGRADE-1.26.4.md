# Upgrade to Portfolio Architect 1.26.4

Version 1.26.4 is a presentation-only cleanup after v1.26.3 live acceptance. It
standardises date-only reference-dashboard tiles on Home Assistant's native
locale-aware short-date rendering. Portfolio calculations, provider acquisition,
source atomicity, identity, authorized cash, entity contracts, and wire schemas are
unchanged.

## Before upgrading

- Keep the existing Comdirect and Trade Republic Gateway configuration unchanged.
- Do not delete the accepted Trade Republic statement snapshot.
- Preserve any local modifications to your copied Lovelace dashboard before
  adopting the updated reference YAML.

## Upgrade

1. Update **Portfolio Architect Gateway — Comdirect** to 1.26.4 in place.
2. Update **Portfolio Architect Gateway — Trade Republic** to 1.26.4 in place.
3. If installed, update **Portfolio Architect Gateway — DKB** to 1.26.4 in place;
   it remains an experimental manual-only non-live shell.
4. Update Portfolio Architect to 1.26.4 through HACS.
5. Restart Home Assistant once after the HACS update.
6. Do not reauthenticate Comdirect, re-enter Gateway tokens, re-import the Trade
   Republic statement, or recreate the Portfolio Architect configuration solely for
   this release.

## Existing copied dashboard

HACS does not overwrite copied/imported Lovelace dashboards. To receive the
v1.26.4 date-display cleanup, deliberately update the copied dashboard from the
current reference YAML.

The affected date-only tiles use only Home Assistant native Tile configuration:

```yaml
state_content: state
time_format:
  type: date
  style: short
```

No locale-specific date attribute or hard-coded date pattern is required. The
existing refresh-schedule timestamps remain on their generic `datetime` / `short`
Tile rendering without seconds.

## Live acceptance

A successful v1.26.4 acceptance requires:

1. The healthy portfolio remains 3 sources / 3 providers / 7 of 7 with Robotics
   held through Trade Republic and existing Comdirect + DKB provenance preserved.
2. The v1.26.3 policy section remains in its accepted compact layout and the German
   unavailable-state fix remains intact.
3. In the German dashboard, Scheduled execution, Next plan review, Last decision,
   Next review, and an overdue review when applicable render in the frontend's
   normal localized short-date style rather than raw ISO `YYYY-MM-DD`.
4. The corresponding English dashboard uses the same generic native Tile contract.
5. Refresh-schedule timestamps remain generic and do not gain seconds-specific
   formatting.
6. No Comdirect reauthentication, Gateway reconfiguration, or Trade Republic
   statement re-import is required.

## Compatibility

- payload schema: 8 (unchanged)
- REST portfolio schema: 1 (unchanged)
- Gateway health schema: 6 (unchanged)
- existing Home Assistant entity IDs / unique IDs: unchanged
- existing machine-readable states and availability semantics: unchanged
- v1.26.3 dashboard/policy behavior: unchanged
- v1.26.2 unavailable-source diagnostics: unchanged
- v1.26.1 ISIN-first identity semantics: unchanged
- v1.26 atomic configured-source/LKG behavior: unchanged
- no trading, order, transfer, payment or transaction-history capability
