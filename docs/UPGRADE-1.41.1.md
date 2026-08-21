# Upgrade to Portfolio Architect 1.41.1

Version 1.41.1 is a narrow correctness hotfix for provider-scoped funding selection. It preserves the v1.41.0 Trade Republic `KONTOAUSZUG` cash importer and changes only the final tie-break used when an execution-provider-local cash candidate and a cross-provider funding candidate are otherwise equal under the existing route economics.

## What changes

When two funded-route candidates have the same:

- total cost ratio;
- funding settlement time;
- configured execution-provider priority;
- executable order amount; and
- combined execution/funding fees,

Portfolio Architect now prefers the candidate that does **not** require a funding transfer before falling through to route/provider identifier tie-breaks.

This prevents an advisory transfer from being invented merely because the funding provider ID sorts before the execution provider ID. It does not override a cheaper route, a faster transfer, an explicit provider-priority preference, a larger executable order, or lower fees.

## Upgrade

1. Update the Portfolio Architect integration to **1.41.1** and restart/reload Home Assistant as required by HACS.
2. Update the Comdirect, DKB, and Trade Republic Gateway Apps in place to **1.41.1** for package alignment.
3. Do not uninstall any Gateway App or remove private App data.
4. No dashboard YAML replacement is required.
5. No broker configuration migration is required.

The Trade Republic App's separate `DEPOTAUSZUG` holdings and `KONTOAUSZUG` cash imports are unchanged from v1.41.0.

## Live acceptance

With fresh Trade Republic local cash sufficient for a Trade Republic purchase and an evidenced zero-fee/zero-business-day Comdirect → Trade Republic edge also available, confirm that Portfolio Architect:

- keeps the Trade Republic execution route;
- uses Trade Republic as the funding provider;
- reports no funding transfer for that purchase;
- leaves Comdirect cash untouched by that purchase; and
- retains zero estimated funding-transfer and execution costs when the selected Trade Republic route itself is zero-fee.

A transfer should still be recommended when destination-local cash is insufficient and the configured transfer-funded route is the best eligible option.
