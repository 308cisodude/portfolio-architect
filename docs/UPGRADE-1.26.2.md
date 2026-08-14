# Upgrade to Portfolio Architect 1.26.2

Version 1.26.2 is a low-risk UX and diagnostics polish release on top of the
live-accepted v1.26.1 multi-provider/ISIN-first baseline. Portfolio calculation,
provider acquisition and all wire schemas remain unchanged.

## What changes

- The German reference dashboard uses explicit German presentation attributes for
  state values instead of inheriting the global Home Assistant frontend language.
- Source-unavailable entities expose privacy-safe source-instance metadata and the
  reference tile names the configured source or sources currently blocking a live
  aggregate.
- Additional REST Gateway failures are collected across all configured supplemental
  Gateways for diagnostic presentation, while aggregation remains atomic.
- DKB CSV source failures receive bounded instance labels without exposing paths.
- `supplemental_source_unavailable` is now a declared and translated attention
  reason, fixing the previous `None` presentation.

## Upgrade procedure

1. Update **Portfolio Architect Gateway — Comdirect** to 1.26.2 in place.
2. Update **Portfolio Architect Gateway — Trade Republic** to 1.26.2 in place.
3. If installed, update **Portfolio Architect Gateway — DKB** to 1.26.2 in place;
   it remains an experimental manual-only non-live shell.
4. Update Portfolio Architect to 1.26.2 through HACS.
5. Restart Home Assistant once after the HACS update.
6. Do not uninstall/reinstall Gateway Apps. Existing private tokens, Comdirect
   authentication state and the accepted Trade Republic snapshot must remain in
   place.

No Comdirect reauthentication, account reselection, cash-policy migration, entity
migration, Trade Republic statement re-import or Gateway reconfiguration is
required solely by this release.

## Existing copied dashboard

HACS does not overwrite copied/imported Lovelace dashboards. To receive the v1.26.2
presentation changes, deliberately update the copied dashboard from the current
reference YAML. The important reference changes are:

- German state-bearing tiles use `state_content: display_state_de` (or the
  equivalent list containing `display_state_de` and another attribute);
- the English Source unavailable tile uses
  `state_content: unavailable_source_summary`;
- the German Quelle fehlt tile uses
  `state_content: unavailable_source_summary_de`; and
- the German Source provider tile continues to use `provider_summary_de`.

## Live acceptance

A successful v1.26.2 acceptance requires:

1. The existing healthy aggregate remains 3 sources / 3 providers / 7 of 7 with
   Robotics held through Trade Republic and existing Comdirect + DKB provenance
   preserved.
2. Comdirect and Trade Republic remain healthy without reauthentication,
   reconfiguration or statement re-import.
3. The updated German dashboard shows German state values even if the global Home
   Assistant frontend language is English.
4. Temporarily stop the Trade Republic App. Portfolio Architect must retain 7/7 and
   source count 3 as degraded/non-actionable Home Assistant LKG.
5. The Source unavailable / Quelle fehlt tile must identify `Trade Republic
   Gateway` / `Trade-Republic-Gateway` rather than showing only a generic outage.
6. The attention reason must show `Supplemental source unavailable` / `Zusätzliche
   Quelle nicht verfügbar`, not `None`; the German recommended action should render
   `Verbindung prüfen`.
7. Start Trade Republic again and confirm automatic recovery to healthy/live 7/7
   without changing Portfolio Architect configuration.

## Compatibility

- payload schema: 8 (unchanged)
- REST portfolio schema: 1 (unchanged)
- Gateway health schema: 6 (unchanged)
- existing Home Assistant entity IDs / unique IDs: unchanged
- existing machine-readable state values: unchanged
- v1.26.1 ISIN-first identity semantics: unchanged
- existing Comdirect authorized-cash semantics: unchanged
- v1.20/v1.20.1 LKG semantics and v1.26 atomic configured-source behavior:
  unchanged
- v1.21 actionability semantics: unchanged
- v1.22 privacy/publication gates: unchanged
- no trading, order, transfer, payment or transaction-history capability
