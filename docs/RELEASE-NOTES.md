# Portfolio Architect 1.42.0

Portfolio Architect v1.42.0 is a **presentation-boundary release**. It exposes the already-decided funding and purchase sequence as a bounded normalized Home Assistant execution-path entity, and the bilingual reference dashboard renders that entity directly through one native Markdown card per locale. The frontend does not recalculate routing, funding, fees, provider choice, or actionability.

## Normalized execution path

A new diagnostic enum sensor, `sensor.portfolio_architect_execution_path`, derives presentation-only instructions from the validated actionable plan after the engine has already made its decisions. The sensor exposes execution-path presentation schema 1 with:

- a bounded ordered `steps` list;
- English and German plain-text instructions;
- English and German pre-rendered Markdown;
- explicit presentation modes `local_cash`, `transfer`, `mixed`, and `purchase_only`.

The presentation adapter consumes the plan's existing decided purchase/funding fields and aggregate `funding_transfers`; it does not import or call route-selection or funded-route-selection code. The path is bounded to 80 total presentation steps and is unavailable when the coordinator does not have an actionable plan.

For execution-provider-local cash, the path explicitly says to use the cash already available at that provider before presenting the purchase. When an advisory funding transfer is part of the decided plan, the path presents the transfer first, including amount, fee, and conservative settlement-business-day evidence, then presents the purchase. Zero settlement business days is described only as **same business day** / **am selben Geschäftstag**; it is never promoted into an instant-transfer SLA.

## Native bilingual dashboard rendering

The v1.39.0 colourful paired allocation Tile view was not included in v1.38.1; it remains present and unchanged alongside the v1.38.1 signed drift presentation.

The reference dashboard adds an **Execution path / Ausführungsweg** block immediately before the existing recommended-purchases section. Each locale uses one core Home Assistant Markdown card whose template does only one thing: read the integration-owned `markdown` or `markdown_de` attribute from the execution-path sensor.

No dashboard Jinja reads `funding_transfers`, provider cash, execution-provider fields, route costs, or business-policy state. There is no custom card, card-mod, auto-entities, JavaScript, or additional frontend dependency. Routing remains owned by the engine/integration; the frontend merely renders the already-decided presentation contract.

Because the reference dashboard itself changes in v1.42.0, users who maintain the supplied bilingual dashboard should replace the complete dashboard YAML with the v1.42.0 version. Integration/HACS updates still never overwrite user-managed Lovelace YAML automatically.

## Advisory-only boundary

The rendered path is explicitly advisory. Portfolio Architect still cannot move cash or place orders. The normalized instructions do not add service calls, provider write methods, transfers, payments, withdrawals, order placement/cancellation, or sell capability.

The v1.41.0 Trade Republic `KONTOAUSZUG`/`DEPOTAUSZUG` acquisition and the v1.41.1 provider-local-cash routing tie-break remain unchanged. Trade Republic PDF parsing remains inside its provider-isolated Gateway App and does not move PDF parsing into Portfolio Architect. Comdirect, DKB, and Trade Republic Gateway runtime behavior is unchanged apart from normal v1.42.0 package/version alignment. DKB live Gateway acquisition remains a later gated milestone; v1.42.0 does not infer authenticated holdings support from anonymous capability evidence.

## Compatibility contracts retained

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported.
- presentation schema 2 remains unchanged; execution-path presentation schema 1 is an additive Home Assistant presentation contract, not a payload-schema change.
- broker schemas 1/2/3 remain unchanged.
- provider-scoped cash, funding-transfer evidence/freshness, cost-first route ordering, and the v1.41.1 local-cash tie-break remain unchanged.
- The v1.33.0 source-freshness and plan-schedule separation remains unchanged: recurring scheduling stays anchored to the latest valid Portfolio Architect evaluation, and v1.42.0 does not change any configured freshness threshold.
- Verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, provider isolation, and fail-closed provider behavior remain unchanged.
- The historical v1.19.0-rc2 state remains historical and is not promoted by this release.
- No trading, order, transfer, payment, or transaction-history capability is introduced by v1.42.0; withdrawal capability is likewise absent.

## Upgrade

Update the integration and all three Gateway Apps in place to v1.42.0. Preserve existing private App state. No broker migration is required. To use the new reference presentation, bulk-replace the complete bilingual dashboard YAML with the v1.42.0 dashboard.
