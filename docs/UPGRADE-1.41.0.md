# Upgrade to Portfolio Architect 1.41.0

Version 1.41.0 adds a separate, bounded Trade Republic `KONTOAUSZUG` cash-statement importer while preserving the established `DEPOTAUSZUG` holdings importer and all existing provider/security boundaries.

## Before upgrading

- Keep the existing Home Assistant integration entry and all Gateway Apps installed in place so private state, TLS trust, bearer tokens, Comdirect OAuth/session state, DKB probe state, and the last accepted Trade Republic holdings snapshot survive.
- Do not uninstall or delete any Gateway App data for a normal upgrade.
- No dashboard YAML replacement is required.

## Upgrade sequence

1. Update the Portfolio Architect integration to **1.41.0** and restart/reload Home Assistant as required by HACS.
2. Update the Comdirect, DKB, and Trade Republic Gateway Apps in place to **1.41.0**.
3. Confirm Portfolio Architect remains healthy/live and all configured Gateways retain verified HTTPS/private-CA trust.
4. Open **Portfolio Architect Gateway — Trade Republic** through admin-only Ingress.
5. Leave the existing `DEPOTAUSZUG` holdings snapshot in place unless a newer depot statement is available.
6. Under **Investment cash**, import a current official German text-PDF `KONTOAUSZUG`.
7. Confirm the page reports an accepted cash statement and a bounded EUR cash timestamp. The uploaded PDF itself must not remain in App storage.
8. Reload/re-evaluate Portfolio Architect and inspect `sensor.portfolio_architect_available_investment_reserve`. A fresh Trade Republic cash snapshot should appear as provider-scoped cash and should suppress an unnecessary cross-provider funding transfer when Trade Republic already holds enough authorized cash for the selected execution route.

## Cash evidence semantics

The economic cash timestamp comes from the statement's `BARMITTELÜBERSICHT` as-of date, not from the later PDF creation time. Holdings and cash timestamps are independent by design. A fresh cash import never makes old holdings appear newer, and a fresh depot statement never refreshes stale cash.

The importer validates the `Cashkonto` arithmetic and reconciles the cash-custody components before accepting the result. Stale cash is excluded from funding decisions using the existing `imported_statement` freshness threshold without invalidating otherwise usable holdings evidence.

## Privacy and security

The Trade Republic App parses uploaded PDFs only in memory. It does not persist raw PDFs, transaction history, transaction descriptions, counterparties, IBAN/account identifiers, names, or addresses. Only the bounded provider-neutral holdings snapshot and bounded normalized cash state are retained in App-private storage.

No unofficial Trade Republic API, credential flow, trading, order, transfer, payment, sale, or withdrawal operation is introduced.

## Rollback

A normal rollback to 1.40.1 does not require deleting the Trade Republic App data. The older App ignores the new sibling cash-state file and continues using the last accepted holdings snapshot. If rollback is required, restore the reviewed prior integration/App release in place and verify provider health before making any additional configuration change.
