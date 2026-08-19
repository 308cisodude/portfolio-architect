# Upgrade to Portfolio Architect 1.35.4

Version 1.35.4 fixes locale-sensitive EUR amount entry and the generic invalid-amount HTTP 400 in the
Comdirect Gateway App cash-authorization form. It is prepared on top of published v1.35.3.

## Recommended upgrade order

1. Update **Portfolio Architect** through HACS to **1.35.4** and restart Home Assistant once.
2. Update **Portfolio Architect Gateway — Comdirect** to **1.35.4** in place. Do not uninstall the App,
   clear `/data/gateway`, or reauthenticate solely because of this upgrade.
3. Confirm Portfolio Architect remains healthy/live with the existing cash policy unchanged.
4. Open the Comdirect App Web UI → **Investment cash authorization**.
5. Test the desired policy using a normal human amount format. For the live regression case,
   **Keep cash reserve** with `1024,00` must be accepted and normalized exactly like `1024.00`.
6. Verify Portfolio Architect reports `authorized_eur = max(eligible_eur - 1024, 0)` after the next
   accepted refresh.
7. Optionally submit a deliberately malformed value such as `12,34,56`; the App must return to its
   own page with bounded validation guidance and must preserve the previously valid policy.
8. Align Trade Republic and DKB Apps to 1.35.4 afterward; their provider behavior is unchanged apart
   from normal package/common-runtime version alignment.

## Accepted human formats

The cash-cap and retained-cash fields accept decimal comma or decimal point plus strictly validated
thousands grouping, including examples such as `1024,00`, `1024.00`, `1.024,00`, `1,024.00` and
space/apostrophe-grouped equivalents. The stored private value remains canonical and locale-neutral.

The parser still rejects signs, exponent notation, mixed or malformed grouping, more than two
fractional digits and values outside the established non-negative EUR bound.

## Existing configuration

No portfolio, dashboard, source, TLS, bearer-token, broker-schema or Home Assistant options migration
is required. Existing `broker.yaml`, Gateway private CA/token, Comdirect OAuth/session state, selected
investment account and last valid investment-cash policy remain in place.

## Rollback

If the live policy is `retain`, return it to `all_available` or `capped` before rolling the Comdirect
App back to a pre-v1.35.2 package, because those older strict clients do not recognize `retain_eur`.
A rollback from 1.35.4 to 1.35.3 otherwise requires no broker or integration migration; the only lost
behavior is the locale-tolerant amount parser and bounded validation message.
