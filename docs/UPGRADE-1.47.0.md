# Upgrade to Portfolio Architect 1.47.0

Version 1.47.0 adds independent DKB Girokonto cash evidence inside the DKB Gateway. Existing DKB holdings, Comdirect, Trade Republic, broker configuration and dashboard presentation require no migration.

## Upgrade order

1. Start from a healthy v1.46.0 installation where DKB is already supplied only by **Portfolio Architect Gateway — DKB**.
2. Update the Portfolio Architect Home Assistant integration to **1.47.0** and restart Home Assistant once.
3. Update **Portfolio Architect Gateway — DKB** to **1.47.0** in place. Preserve its App-private `/data` state.
4. Align Comdirect and Trade Republic Gateway Apps to 1.47.0 as normal package-version hygiene; their acquisition behavior is unchanged.
5. Open the DKB Gateway Ingress page. Existing depot holdings should still be present and a separate **DKB Girokonto Umsatzliste CSV** cash-import control should now be visible.
6. Export the current DKB Girokonto Umsatzliste CSV and import it through the new cash control.
7. Confirm the DKB Gateway shows active private cash and Portfolio Architect remains healthy after its next refresh/reload.
8. Confirm provider-scoped cash now includes a DKB row with the explicit positive account balance (or EUR 0 if the account balance is non-positive), while Comdirect/TR cash and existing routing remain otherwise unchanged.

## Privacy and cash semantics

The DKB cash importer does not persist the raw Umsatzliste, account identifier, transaction rows, counterparties or payment references. It persists only normalized balance/date evidence.

Only the explicit dated EUR `Kontostand` is used. Transaction history is not summed to reconstruct a balance. A negative balance never becomes investable cash and no overdraft or credit facility is inferred.

## Freshness

DKB holdings and cash have separate evidence clocks:

- DKB depot holdings remain governed by the configured `gateway_snapshot` freshness threshold;
- DKB Girokonto cash is governed by the configured `imported_statement` freshness threshold, matching Trade Republic cash.

Importing one evidence family does not refresh the other.

## No other migration

No dashboard YAML replacement, broker configuration change, Comdirect reauthentication, Trade Republic re-import or FinTS probe is required solely because of v1.47.0.
