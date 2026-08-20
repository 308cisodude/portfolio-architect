# Upgrade to Portfolio Architect v1.39.0

Portfolio Architect v1.39.0 is a presentation-only follow-up to the live-accepted v1.38.1 release. It adds paired colourful native allocation Tiles for the existing 32 bounded generic target presentation slots. Provider acquisition, portfolio calculations, execution/funding semantics, private state and Gateway wire/security contracts are unchanged.

## Before upgrading

- Keep the existing Portfolio Architect private state and provider configuration in place.
- Do not delete or recreate the integration or any Gateway App.
- If you maintain a personalized dashboard, save your current YAML before replacing it.
- No trade, cash transfer, provider reauthentication, Trade Republic statement re-import or DKB capability probe is required solely for this release.

## Upgrade sequence

1. Update the HACS integration to v1.39.0 and restart Home Assistant.
2. Confirm Portfolio Architect returns to its expected healthy/live state.
3. Align the Comdirect, DKB and Trade Republic Gateway Apps to v1.39.0 in place. Their runtime behavior is unchanged; this is package/version alignment.
4. HACS does not overwrite user-owned Lovelace YAML. Bulk-replace the copied dashboard with `portfolio-architect-v1.39.0-bilingual-dashboard.yaml` to adopt the new presentation, then hard-refresh the frontend.

## What to verify

In both English and German views:

- **Current plan allocation** and **Plan target allocation** show one Tile per configured target and no unused placeholders;
- the corresponding current and target Tile for a position use the same identity colour;
- allocation Tiles use a native 0–100% bar gauge and dynamic instrument names;
- a configured target with 0% current allocation would remain visible because Tile membership is keyed to its positive target allocation;
- the v1.38.1 signed drift section remains amber/green/red by underweight/on-target/overweight status and retains its -100…+100 pp scale;
- tapping a drift Tile still opens the matching allocation explanation;
- tapping a recommended purchase still opens the copy-friendly ISIN entity and holding it still opens the purchase explanation;
- policy-aware authorized-cash context remains present when complete validated evidence exists.

## Compatibility

- payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged;
- presentation schema 2: unchanged;
- broker schemas 1/2/3: unchanged;
- verified private-PKI HTTPS and bearer authentication: unchanged.

Rollback is presentation-safe: restore the previous dashboard YAML and prior reviewed release together if rollback is required. Do not move or rewrite an already published immutable tag.
