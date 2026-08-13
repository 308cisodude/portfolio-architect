# Upgrade to Portfolio Architect 1.23.0

Version 1.23.0 introduces the provider-aware Gateway foundation. The existing live
Gateway remains Comdirect-specific, but the hardened server no longer depends on a
Comdirect client type and Gateway health now identifies the provider explicitly.

## What changes

- The existing Home Assistant App is displayed as **Portfolio Architect Gateway — Comdirect**.
- Its existing slug `portfolio_architect_gateway`, private App data, API token,
  Comdirect credentials/session, selected investment account, cash policy and
  cached snapshot are retained.
- Gateway health schema 6 adds the bounded non-secret field `provider_id`.
- Portfolio Architect requests health schema 6 with backward-compatible fallbacks
  to schemas 5 through 1.
- Gateway status attributes and diagnostics can show `provider_id`; no account or
  depot identifier is added.
- A provider-neutral `PortfolioProvider` runtime contract is introduced for future
  DKB and Trade Republic Gateway Apps.

## Upgrade procedure

1. Update **Portfolio Architect Gateway — Comdirect** to 1.23.0 through
   **Settings → Apps**.
2. Update **Portfolio Architect** to 1.23.0 through HACS.
3. Restart Home Assistant once after the HACS update.
4. Confirm `Version` reports 1.23.0 and normal live health returns.
5. Open the Gateway status entity and confirm `health_schema_version: 6` and
   `provider_id: comdirect`.

No Comdirect reauthentication, account reselection, cash-policy migration,
configuration-entry migration, entity migration or dashboard replacement is
required solely because of this upgrade.

## Compatibility

- payload schema: 8 (unchanged)
- REST portfolio schema: 1 (unchanged)
- Gateway health schema: 6 (additive provider identity; schemas 1–5 retained)
- existing entity IDs / unique IDs: unchanged
- authorized-cash and LKG semantics: unchanged
- v1.21 schedule/actionability semantics: unchanged
- no DKB or Trade Republic live acquisition runtime yet
- no trading, order, transfer, payment, or transaction-history capability
