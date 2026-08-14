# Portfolio Architect 1.26.4

Version 1.26.4 is a narrow reference-dashboard formatting follow-up to v1.26.3.
Live acceptance of v1.26.3 confirmed the multi-provider, degraded/LKG, German
unavailable-state and policy-layout behavior, but exposed one remaining visual
inconsistency: date-only Tile cards still rendered the native ISO `YYYY-MM-DD`
state instead of using Home Assistant's locale-aware date presentation.

## Native date-tile formatting

The reference dashboards now request Home Assistant's native Tile formatter for
all date-only state tiles:

- Scheduled execution / Geplante Ausführung;
- Next plan review / Nächste Planprüfung;
- Last decision / Letzte Entscheidung;
- Next review / Nächste Prüfung; and
- Overdue review / Überfällige Prüfung.

Each tile keeps `state_content: state` and uses the generic Home Assistant
`time_format` map with `type: date` and `style: short`. No locale-specific date
string, template, helper entity, or presentation attribute is introduced.

The underlying entities remain native `SensorDeviceClass.DATE` sensors with native
`date` values. Their machine-readable state/availability contracts therefore stay
unchanged for automations, templates, recorder history, and API consumers.

## Refresh timestamps remain generic

The existing refresh-schedule tiles retain their native `datetime` / `short`
formatting. No explicit `HH:MM:SS` format and no seconds-specific presentation
layer is added.

## Compatibility

Portfolio payload schema 8, REST portfolio schema 1, and Gateway health schema 6
remain unchanged; health schemas 1–5 remain supported for backward compatibility.

- Portfolio payload schema: 8 (unchanged)
- REST portfolio schema: 1 (unchanged)
- Gateway health schema: 6 (unchanged; schemas 1-5 remain supported)
- Existing Home Assistant entity IDs / unique IDs: unchanged
- Existing machine-readable states and availability semantics: unchanged
- v1.26.3 policy-layout and German unavailable-state behavior: unchanged
- v1.26.2 unavailable-source diagnostics: unchanged
- v1.26.1 ISIN-first identity and fail-closed collision behavior: unchanged
- v1.26 configured-source atomic LKG behavior: unchanged
- Comdirect authentication/account selection/authorized cash: unchanged
- Trade Republic statement import and persisted snapshot: unchanged
- DKB Gateway: still experimental/manual-only/fail-closed, no acquisition path
- No trading/order/transfer/payment/transaction-history capability

No trading, order, transfer, payment, or transaction-history capability is added by this release.

DKB live Gateway acquisition remains a later provider-specific milestone; v1.26.4
does not promote the experimental DKB shell into a live acquisition source. The
release does not move PDF parsing into Portfolio Architect: Trade Republic statement
parsing remains isolated in the Trade Republic Gateway App.

The historical experimental `v1.19.0-rc2` brokerage diagnostics/fee-probe work
remains separate and is not promoted by this release.

Gateway HTTPS transport hardening remains the next security milestone in v1.27.0.
