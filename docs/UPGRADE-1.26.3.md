# Upgrade to Portfolio Architect 1.26.3

Version 1.26.3 is a presentation-only follow-up to v1.26.2. It fixes one remaining
German unavailable-state dashboard edge case and simplifies the policy-compliance
reference layout. Portfolio calculation, acquisition, source atomicity, identity,
authorized-cash semantics and all wire schemas are unchanged.

## Before upgrading

- Keep the existing Comdirect and Trade Republic Gateway configuration unchanged.
- Do not delete the accepted Trade Republic statement snapshot.
- If you maintain local modifications to the copied Lovelace dashboard, preserve
  them before adopting the updated reference YAML.

## Upgrade

1. Update **Portfolio Architect Gateway — Comdirect** to 1.26.3 in place.
2. Update **Portfolio Architect Gateway — Trade Republic** to 1.26.3 in place.
3. If installed, update **Portfolio Architect Gateway — DKB** to 1.26.3 in place;
   it remains an experimental manual-only non-live shell.
4. Update Portfolio Architect to 1.26.3 through HACS.
5. Restart Home Assistant once after the HACS update.
6. Do not reauthenticate Comdirect, re-enter Gateway tokens, re-import the Trade
   Republic statement, or recreate the Portfolio Architect configuration solely for
   this release.

## Existing copied dashboard

HACS does not overwrite copied/imported Lovelace dashboards. To receive the v1.26.3
presentation/layout changes, deliberately update the copied dashboard from the
current reference YAML.

The important changes are:

- German **Zugeordnet** and **Käufe** tiles use the always-available
  `sensor.portfolio_architect_plan_actionability` entity with
  `recommended_total_display_de` / `purchase_count_display_de`, while their
  more-info actions still target the original sensors;
- the aggregate **Checks / Prüfungen** and **Opportunities / Optimierung** tiles are
  removed from the primary policy section only;
- their native entities remain available unchanged;
- the exception lifecycle is ordered as Exceptions → Robotics exception, then Last decision → Next/overdue review; and
- the German lifecycle labels are explicit and independent of the frontend
  language.

## Live acceptance

A successful v1.26.3 acceptance requires:

1. The healthy portfolio remains 3 sources / 3 providers / 7 of 7 with Robotics
   held through Trade Republic and existing Comdirect + DKB provenance preserved.
2. Comdirect and Trade Republic remain healthy without reauthentication,
   reconfiguration or statement re-import.
3. The updated policy section omits the aggregate Checks/Opportunities counters but
   retains the concrete optimisation tiles and coherent exception lifecycle.
4. Temporarily stop Trade Republic and wait for a Portfolio Architect refresh.
5. The complete 7/7 aggregate and source count 3 remain visible as
   degraded/non-actionable Home Assistant LKG.
6. `Quelle fehlt` still identifies `Trade-Republic-Gateway`; the reason remains
   `Zusätzliche Quelle nicht verfügbar`; the recommended action remains
   `Verbindung prüfen`.
7. **Zugeordnet** and **Käufe** render `Nicht verfügbar` rather than `Unavailable`.
8. Start Trade Republic and confirm automatic recovery to healthy/live 7/7 without
   changing Portfolio Architect configuration.

## Compatibility

- payload schema: 8 (unchanged)
- REST portfolio schema: 1 (unchanged)
- Gateway health schema: 6 (unchanged)
- existing Home Assistant entity IDs / unique IDs: unchanged
- existing machine-readable states and availability semantics: unchanged
- v1.26.2 unavailable-source diagnostics: unchanged
- v1.26.1 ISIN-first identity semantics: unchanged
- v1.26 atomic configured-source/LKG behavior: unchanged
- no trading, order, transfer, payment or transaction-history capability
