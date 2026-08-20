# Upgrade to Portfolio Architect 1.38.1

Portfolio Architect 1.38.1 is a narrow Home Assistant dashboard-presentation follow-up to the exact published v1.38.0 baseline. It restores native dynamic signed allocation-drift bars for the existing bounded target presentation slots. Provider acquisition, portfolio calculations, private state, Gateway wire/security contracts, execution/funding semantics and the advisory/no-trading boundary are unchanged.

The v1.38.0 policy-aware cash context and copy-friendly recommended-purchase ISIN interaction are preserved.

## Dashboard ownership

HACS updates the integration package but does not overwrite an imported or personalized Lovelace dashboard. To adopt the v1.38.1 presentation, deliberately replace or merge the reference dashboard after the integration update. Bulk replacement with the supplied bilingual dashboard is the preferred low-risk path when you use the project reference dashboard as your source.

## Upgrade sequence

1. Update the Portfolio Architect HACS integration to 1.38.1 and restart Home Assistant.
2. Confirm the integration returns to the same expected healthy/live or deliberately degraded state before changing any dashboard YAML.
3. Align the Comdirect, DKB and Trade Republic Gateway Apps to 1.38.1 in place. Preserve their existing private state, tokens, trust material and provider configuration; no reauthentication is required solely because of this release.
4. Bulk-replace the user-owned dashboard YAML with `portfolio-architect-v1.38.1-bilingual-dashboard.yaml` (or deliberately merge the allocation section if you maintain a custom dashboard), then reload/hard-refresh the frontend.
5. In **Current portfolio allocation**, confirm each configured target exposes exactly one visible drift Tile while unused trailing target slots remain hidden.
6. Confirm the status presentation: underweight is amber, on target is green, and overweight is red.
7. Confirm the Tile-native signed bar gauge uses the same numeric drift state in percentage points and a fixed -100…+100 range.
8. Tap a drift Tile and verify Home Assistant opens the matching target slot's allocation-explanation entity.
9. Confirm target names remain dynamic and there is no instrument-specific target inventory in the dashboard YAML.
10. Recheck the v1.38.0 dashboard behavior: recommended-purchase tap opens the matching ISIN entity, hold opens the purchase explanation, and the authorized/remaining-cash Tiles retain their policy-aware context.

No real trade, funding transfer, Comdirect PhotoTAN reauthentication, Trade Republic statement re-import or DKB capability probe is required for v1.38.1 acceptance.

## Rollback

If the new native drift presentation misbehaves in the installed Home Assistant frontend, restore the v1.38.0 integration and reference dashboard. The release does not migrate private provider state or change REST/health/presentation/broker schemas, so rollback requires no provider-state conversion. Keep the published v1.38.0 tag and artifacts immutable.
