# Upgrade to Portfolio Architect 1.44.0

Version 1.44.0 is a native Configure UX consistency release. It does not change planning economics, evidence freshness semantics, provider acquisition, Gateway wire schemas, dashboard presentation, or Portfolio Architect's advisory-only boundary.

## Visible edit context

When an existing object is selected for editing, Portfolio Architect now displays a non-editable identity line above the editable fields:

- execution provider: provider display name and immutable provider ID;
- savings-plan route: provider display name, immutable provider ID, and ISIN;
- funding transfer: exact directed source-provider → destination-provider relationship, including provider IDs.

This context is informational only. The immutable route/edge/provider identity is still carried internally by the options flow and cannot be changed by editing the economic/evidence fields.

The plan-instrument editor already displayed instrument name, ISIN, WKN, and target ID and remains unchanged.

## Configure menu consistency

All Configure menus are covered by bilingual regression checks. Every menu action must have a non-empty English and German label and a translated destination title. The Funding topology menu explicitly includes the visible **Edit funding transfer / Finanzierungsbeziehung bearbeiten** action.

Home Assistant caches backend translation resources for the running Core process. Because this release changes options-flow strings, perform a full Home Assistant restart after installing the HACS integration update before judging the new labels/context.

## Upgrade procedure

1. Update the Portfolio Architect integration to **1.44.0**.
2. Restart Home Assistant so the updated Configure translations are loaded.
3. Align the Comdirect, DKB, and Trade Republic Gateway Apps to **1.44.0** in place.
4. Confirm Portfolio Architect remains healthy/live and the current plan is unchanged.
5. No dashboard YAML replacement is required.
6. Existing `broker.yaml` remains valid and requires no migration.

## Suggested live acceptance

Keep the intentionally mixed v1.43 route-evidence state for the first test:

1. Open the already explicit Trade Republic route for `IE00BJ0KDQ92` and verify the edit form identifies Trade Republic/provider ID + ISIN above the fields.
2. Open one of the six remaining legacy/fallback Trade Republic routes and verify the same identity context is shown while provider-level evidence is pre-filled.
3. Optionally submit that legacy route unchanged to prove the v1.43 fallback-to-explicit migration still works.
4. Open **Configure → Execution providers & funding → Funding topology** and verify the **Edit funding transfer** menu label is visible.
5. Open the existing Comdirect → Trade Republic edge and verify that exact directed relationship is shown non-editably above fee/settlement/evidence fields.
6. Save unchanged and confirm local Trade Republic cash routing and execution costs remain unchanged.

## Preserved boundaries

- broker schemas 1/2/3 remain unchanged;
- payload schema 8, REST portfolio schema 1, Gateway health schema 6, and presentation schema 2 remain unchanged;
- v1.43 route-level savings-plan evidence and legacy provider-evidence fallback are unchanged;
- v1.41 Trade Republic holdings/cash acquisition and v1.41.1 local-cash tie-break are unchanged;
- v1.42 execution-path presentation is unchanged;
- Comdirect/DKB/Trade Republic provider acquisition is unchanged apart from normal version alignment;
- verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning, and provider isolation are unchanged;
- no transfer initiation, payment API, trading, order placement/cancellation, sell, withdrawal, or transaction-history capability is added.
