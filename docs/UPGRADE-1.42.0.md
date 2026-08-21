# Upgrade to Portfolio Architect 1.42.0

Version 1.42.0 adds a normalized, presentation-only execution path for the already-decided actionable plan. It does not change provider acquisition, route selection, funding economics, schemas, or Portfolio Architect's advisory-only boundary.

## What changes

The Home Assistant integration adds `sensor.portfolio_architect_execution_path`. When a plan is actionable, the entity exposes a bounded ordered instruction path that describes the decisions Portfolio Architect has already made, for example:

- use existing provider-local cash, then buy the selected instrument; or
- transfer the advised amount between configured providers, then buy the selected instrument at the chosen execution provider.

The entity publishes structured steps plus English/German text and Markdown attributes. This is a rendering contract only: it consumes the engine's decided purchase/funding fields and never reruns route or funding selection.

The supplied bilingual reference dashboard adds a native **Execution path / Ausführungsweg** Markdown block before **Recommended purchases / Empfohlene Käufe**. The Markdown card simply renders the integration-owned localized attribute; it contains no routing or funding business logic.

## Upgrade

1. Update the Portfolio Architect integration to **1.42.0** and restart/reload Home Assistant as required by HACS.
2. Align the Comdirect, DKB, and Trade Republic Gateway Apps to **1.42.0** in place.
3. Do not uninstall any Gateway App or remove private App data.
4. No broker configuration migration is required.
5. **Bulk-replace the complete bilingual dashboard YAML** with the v1.42.0 reference dashboard if you use the supplied dashboard.

## Live acceptance

With the current provider-local Trade Republic cash sufficient for the actionable Trade Republic purchase, confirm that the new dashboard block says to use the existing Trade Republic cash and then buy the selected instrument at Trade Republic, while the underlying reserve sensor still reports no funding transfer.

For a future plan that legitimately requires an evidenced funding transfer, confirm that the same block presents the transfer step before the purchase, including the transfer amount, fee, and conservative settlement-business-day wording.

The execution-path footer must continue to state that Portfolio Architect is advisory only and does not move cash or place orders.
