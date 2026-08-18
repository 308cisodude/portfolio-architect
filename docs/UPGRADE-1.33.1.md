# Upgrade to Portfolio Architect 1.33.1

Version 1.33.1 fixes the recurring plan-calendar anchor exposed during v1.33.0 live
acceptance. Source freshness, provider runtimes and wire schemas are unchanged.

## Upgrade order

1. Update **Portfolio Architect** through HACS to 1.33.1 and restart Home Assistant once.
2. Keep the existing v1.33 evidence-kind freshness policy unchanged.
3. Keep the restored recurring schedule unchanged.
4. Update **Portfolio Architect Gateway — Comdirect** to 1.33.1 in place.
5. Update **Portfolio Architect Gateway — Trade Republic** to 1.33.1 in place.
6. Update **Portfolio Architect Gateway — DKB** to 1.33.1 in place.

Preserve every App-private `/data` volume. Do not recreate sources, replace bearer
tokens, change private-CA trust, reauthenticate Comdirect, re-import the Trade
Republic statement, re-enter the DKB FinTS registration, or run another DKB probe
merely because of this hotfix.

No dashboard replacement, portfolio-plan migration, source migration or Gateway-wire
migration is required.

No dashboard replacement is required. There is no portfolio-plan, config-entry, bank-authentication or Gateway-wire migration.
Do not reauthenticate Comdirect solely because of this release when the current session is healthy.

The DKB FinTS research boundary is unchanged: the existing product registration remains configured, `HIWPDS` remains bank-level capability evidence only, and authenticated user-capability/UPD validation is still required before any future holdings implementation. This hotfix does not yet enable live DKB acquisition and adds no holdings operation.

## What changes

v1.33.0 correctly separated source-evidence freshness from recurring review cadence,
but `plan_review_schedule()` still preferred the oldest contributing source timestamp
as its calendar anchor. A valid old document source could therefore move the plan
calendar into the past even while freshness was correctly satisfied.

v1.33.1 uses the existing latest valid Portfolio Architect evaluation timestamp for
recurring schedule calculations. Source timestamps remain confined to source
freshness/evidence diagnostics.

For the live acceptance topology on 18 August 2026 with a monthly execution day of 7
and a two-day review lead, the expected dates are:

- Scheduled execution: **7 September 2026**
- Next plan review: **5 October 2026**

The 31-July DKB CSV remains governed only by the configured imported-CSV freshness
limit and must not move either schedule date.

## Preserved boundaries

- payload schema 8 unchanged
- REST portfolio schema 1 unchanged
- Gateway health schema 6 unchanged; older supported schemas remain supported
- v1.33 evidence-kind freshness thresholds unchanged
- one-stale-source fail-closed actionability unchanged
- target-plan/schedule persistence separation unchanged
- Comdirect acquisition/OAuth/session/PhotoTAN/cash unchanged
- Trade Republic statement import/private diagnostics unchanged
- DKB anonymous FinTS probe unchanged and still non-live
- private-PKI HTTPS/bearer/DNS/no-plaintext-fallback unchanged
- no trading, order, automatic sell, transfer, payment or transaction-history capability
