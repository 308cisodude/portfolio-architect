# Upgrade to Portfolio Architect v1.40.1

Portfolio Architect v1.40.1 is a Home Assistant Configure-menu compatibility and validation hotfix for v1.40.0. It does not change broker schemas, route economics, funding semantics, provider acquisition, Gateway wire contracts or dashboard presentation.

## What this fixes

- The **Add savings-plan route** and **Edit savings-plan route** forms no longer fail with Home Assistant HTTP 400. Their percentage `NumberSelector` now uses the finest step accepted by Home Assistant Core 2026.8.1 (`0.001` instead of the invalid `0.0001`). Typed box input is not rounded by Home Assistant, so this removes the selector-construction failure without reducing practical fee precision.
- Broker evidence dates now use Home Assistant's native **DateSelector** instead of free-text fields. New provider/funding-evidence forms preselect the current Home Assistant-local date; provider edits preserve the stored date.
- Broker-editor validation now carries the Home Assistant-local evaluation date through load, mutation and atomic write validation, avoiding a UTC/local-date boundary false rejection around local midnight.
- Duplicate provider IDs, savings-plan routes and directed funding transfers receive specific bounded field errors instead of the generic invalid-configuration banner.
- The complete Portfolio Architect **Configure** surface was audited against Home Assistant Core 2026.8.1 selector contracts. All 31 rendered options-flow steps have matching English/German translations and all literal menu destinations resolve to implemented steps; no additional invalid selector configuration was found.

## Upgrade sequence

1. Update the HACS integration to v1.40.1 and restart Home Assistant.
2. Confirm Portfolio Architect returns healthy/live.
3. Align the Comdirect, DKB and Trade Republic Gateway Apps to v1.40.1. Their runtime behavior is unchanged; this is version alignment only.
4. No dashboard YAML replacement is required. The v1.39.0 colourful allocation presentation and v1.38.1 signed drift presentation remain current.
5. Re-open **Portfolio Architect → Configure → Execution providers & funding → Savings-plan routes → Add savings-plan route**. The form should now render normally.
6. When recording new broker evidence, use the native date picker. The new-entry picker defaults to today's Home Assistant-local date; change it to the actual evidence date when the evidence predates today.

## Live regression to resume

The v1.40.0 live test already established official Trade Republic evidence for `IE00BJ0KDQ92` and a verified Comdirect → Trade Republic funding edge. After v1.40.1 is installed, add the Trade Republic savings-plan route through the native editor and continue the cost-first route-selection test. No manual `broker.yaml` edit should be necessary.

## Compatibility

- payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged;
- presentation schema 2: unchanged;
- broker schemas 1/2/3: unchanged;
- provider-scoped cash and evidence-backed directed funding topology: unchanged;
- verified private-PKI HTTPS and bearer authentication: unchanged;
- provider acquisition and Comdirect/DKB/Trade Republic runtime behavior: unchanged;
- no trading, order, transfer, payment or transaction-history capability added;
- no dashboard migration required.

Rollback from v1.40.1 to v1.40.0 does not require data conversion. Existing evidence-backed schema-3 broker documents remain valid. Never move or rewrite an already published immutable tag.
