# Upgrade to Portfolio Architect 1.25.0

Version 1.25.0 adds supported local Trade Republic `DEPOTAUSZUG` statement import
inside the separate Trade Republic Gateway App. Comdirect and DKB runtime behavior
is otherwise unchanged.

## Existing Comdirect installation

1. Update **Portfolio Architect Gateway — Comdirect** to 1.25.0 in place.
2. Update Portfolio Architect to 1.25.0 through HACS.
3. Restart Home Assistant once after the HACS update.
4. Confirm normal live health, `health_schema_version: 6`, and
   `provider_id: comdirect`.

No Comdirect reauthentication, account reselection, API-token change, cash-policy
migration, configuration-entry migration, entity migration or dashboard replacement
is required solely because of this upgrade.

## Trade Republic statement import

1. Update/install **Portfolio Architect Gateway — Trade Republic** 1.25.0.
2. Start the App manually and open its admin-only Ingress page.
3. Select a current supported German text-PDF **DEPOTAUSZUG** document and choose
   **Import statement**.
4. On success, confirm the page reports an active private snapshot and Gateway
   status becomes healthy/live.
5. The original PDF is not retained by the App. Only the normalized holdings
   snapshot and the existing private Gateway bearer token persist.

Encrypted PDFs, scanned/image-only statements, unsupported document families,
ambiguous layouts, or statements whose position count / EUR total does not match the
parsed holdings are rejected without replacing the last accepted snapshot.

Do not publish screenshots of the Ingress page containing the bearer token. Real
Trade Republic statements remain private input and must never be committed as test
fixtures.

## Current aggregation boundary

Version 1.25.0 makes the Trade Republic App a functional manual statement provider,
but Portfolio Architect still configures one primary REST Gateway plus its existing
supplemental CSV sources. Simultaneous Comdirect + Trade Republic REST aggregation
is a separate future configuration milestone.

## Compatibility

- payload schema 8 unchanged
- REST portfolio schema 1 unchanged
- Gateway health schema 6 unchanged
- existing entity IDs / unique IDs unchanged
- authorized-cash, LKG and actionability semantics unchanged
- no trading/order/transfer/payment/transaction-history capability
