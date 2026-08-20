# Upgrade to Portfolio Architect 1.38.0

Version 1.38.0 is a presentation/usability release over the live-accepted v1.37.0 baseline. It adds copy-friendly ISIN access to dynamic recommended-purchase rows and policy-aware investment-cash context to the native dashboard. Provider acquisition/runtime behavior and all Gateway wire/security contracts are unchanged.

## Before upgrading

Start from a healthy v1.37.0 installation. Do not remove App-private state, reauthenticate Comdirect, re-import the Trade Republic statement, change cash policy, or run a DKB probe solely because of this upgrade.

The release changes the reference dashboard. HACS does not overwrite a copied/personalized Lovelace dashboard, so keep a backup of the current YAML before replacing it.

## Upgrade

1. Update Portfolio Architect through HACS to 1.38.0 and restart Home Assistant once.
2. Confirm the existing provider/cash/funding state returns healthy before changing the dashboard.
3. Align the Comdirect, Trade Republic and DKB Gateway Apps to 1.38.0 in place. Their runtime semantics are unchanged.
4. Bulk-replace the user's copied Portfolio Architect Lovelace YAML with the supplied `portfolio-architect-v1.38.0-bilingual-dashboard.yaml`.
5. Hard-refresh the browser once if necessary.

## Live acceptance

Verify the existing healthy baseline first: Source healthy, Gateway status OK, Operating mode Live for live providers, snapshot integrity verified, provider counts unchanged, and DKB still deliberately non-live/manual-only.

Then verify the two v1.38.0 presentation changes:

1. **Authorized investment cash** shows the authorized amount plus a second context line containing total available cash and policy-excluded cash. Confirm `authorized + excluded = total available` to cent precision.
2. **Cash after recommended purchases** shows remaining cash plus total available, policy-excluded and planned cash. Confirm `remaining + excluded + planned = total available` to cent precision.
3. Test all configured cash-policy modes only if convenient; no policy change is required for acceptance. For the current mode, the excluded amount must reflect the actual amount withheld by policy.
4. In **Recommended purchases**, tap a visible purchase row. Native more-info should open the corresponding presentation-slot ISIN entity with a copy-friendly ISIN state.
5. Hold the same purchase row. Native more-info should open its purchase-explanation entity.
6. Confirm the English and German views expose the same recommendation inventory and cash semantics with locale-appropriate formatting.
7. Confirm dynamic targets, outside-scope holdings, active policy findings and allocation-status lists still reconcile and no unavailable trailing slots are shown.

No real trade, transfer, Comdirect reauthentication, Trade Republic re-import, or DKB probe is required for v1.38.0 live acceptance.

## Security and compatibility

This release does not add or alter credentials, provider identifiers, transaction history, trading, orders, payments, transfers or automatic-sell behavior. Payload schema 8, REST portfolio schema 1, Gateway health schema 6, presentation schema 2, broker schemas 1/2/3, verified private-PKI transport and the v1.37 shared human-input validation contract remain unchanged.
