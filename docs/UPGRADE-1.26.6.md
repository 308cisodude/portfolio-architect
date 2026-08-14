# Upgrade to Portfolio Architect 1.26.6

Version 1.26.6 is a narrow diagnostics hotfix for the primary-Gateway degraded-state
edge case found during v1.26.5 live acceptance. It changes no portfolio calculation,
provider acquisition, authentication flow, source atomicity, entity identity, or
wire schema.

## Before upgrading

- Keep the existing Comdirect and Trade Republic Gateway configuration unchanged.
- Do not delete App data, OAuth/session state, the selected Comdirect investment
  account, cash-policy state, or the accepted Trade Republic statement snapshot.
- No copied-dashboard update is required for this release; the existing v1.26.5
  dashboard already consumes `unavailable_source_summary`.

## Upgrade

1. Update **Portfolio Architect Gateway — Comdirect** to 1.26.6 in place.
2. Update **Portfolio Architect Gateway — Trade Republic** to 1.26.6 in place.
3. If installed, update **Portfolio Architect Gateway — DKB** to 1.26.6 in place;
   it remains an experimental manual-only non-live shell.
4. Update Portfolio Architect to 1.26.6 through HACS.
5. Restart Home Assistant once after the HACS update.
6. Do not reauthenticate Comdirect, re-enter Gateway tokens, re-import the Trade
   Republic statement, or recreate the Portfolio Architect configuration solely for
   this release.

## Live acceptance

A successful v1.26.6 acceptance requires:

1. Healthy operation remains 3 sources / 3 providers / 7 of 7 with the established
   provider provenance and actionability behavior unchanged.
2. If Comdirect later enters `reauthentication_required` while its Gateway remains
   reachable and serves its trusted cached snapshot, Portfolio Architect keeps the
   complete aggregate as degraded/non-actionable data.
3. **Source unavailable** identifies **Comdirect Gateway** rather than `None`.
4. **Gateway status**, **Operating mode**, attention reason/action, LKG indicators,
   and the existing date presentation continue to reflect the established state.
5. After successful Comdirect reauthentication, Portfolio Architect recovers to
   healthy/live operation without configuration changes.

## Compatibility

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged
- existing entity IDs / unique IDs: unchanged
- v1.26.5 date-domain presentation contract: unchanged
- provider authentication/acquisition behavior: unchanged
- no trading/order/transfer/payment/transaction-history capability
