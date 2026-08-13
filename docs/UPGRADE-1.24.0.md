# Upgrade to Portfolio Architect 1.24.0

Version 1.24.0 publishes distinct Comdirect, DKB and Trade Republic Home Assistant App identities. Existing Portfolio Architect and Comdirect behavior remains compatible.

## Existing Comdirect installation

1. Update **Portfolio Architect Gateway — Comdirect** to 1.24.0 in place. Do not uninstall it.
2. Update Portfolio Architect to 1.24.0 through HACS.
3. Restart Home Assistant once after the HACS update.
4. Confirm normal live health, `health_schema_version: 6`, and `provider_id: comdirect`.

No Comdirect reauthentication, account reselection, API-token change, cash-policy migration, configuration-entry migration, entity migration or dashboard replacement is required solely because of this upgrade.

## New DKB and Trade Republic packages

The App repository now also contains **Portfolio Architect Gateway — DKB** and **Portfolio Architect Gateway — Trade Republic**. In 1.24.0 these are intentionally experimental, manual-only provider shells. Installing them is optional; do not configure Portfolio Architect to use them as portfolio sources yet.

If started solely for acceptance testing, their admin Ingress page must state that acquisition is not implemented, health schema 6 must identify `dkb` or `trade_republic`, and the portfolio endpoint must remain unavailable rather than manufacturing data.

Trade Republic statement-document import is planned for v1.25.0.

## Compatibility

- payload schema 8 unchanged
- REST portfolio schema 1 unchanged
- Gateway health schema 6 unchanged
- existing entity IDs / unique IDs unchanged
- authorized cash, LKG and actionability semantics unchanged
- no trading/order/transfer/payment/transaction-history capability
