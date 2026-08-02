# Portfolio source adapters

Portfolio Architect normalizes every provider into the same canonical position
model before policy and investment-plan calculations begin.

## Comdirect REST

The stable Gateway App exposes a read-only authenticated local REST snapshot.
The integration validates the schema, timestamp, position count, SHA-256 digest,
and ETag before accepting it.

## Comdirect CSV

The adapter reads the securities table from the German Comdirect depot export.
It imports all valid security types and uses the explicit `Wert in EUR` value.

## DKB CSV

The DKB depot export provides `Bewertungskurs` and `Stückzahl`, not an explicit
market-value column. Portfolio Architect calculates each position with exact
Decimal arithmetic:

```text
market value = valuation price × quantity
```

The adapter preserves WKN and ISIN, maps DKB asset classes into canonical types,
and deliberately ignores depot number, entry price, and performance columns.
The source timestamp is the export date contained in the DKB file.

## Generic EUR CSV

The generic adapter requires explicit mappings for identifier, name, and market
value. Optional mappings cover ISIN, type, and currency. It does not derive values
from price and quantity and does not perform currency conversion.

## Multi-source consolidation

One primary source can be combined with up to eight supplemental DKB exports.
The sources are validated independently and consolidated using these rules:

1. ISIN is the canonical cross-source identity when present.
2. WKN is used only when no ISIN is available.
3. EUR values are summed without intermediate rounding.
4. The primary source supplies the canonical display name and WKN.
5. WKN or instrument-type discrepancies become diagnostic conflicts.
6. The oldest contributing source timestamp controls freshness.
7. A failed supplemental source does not replace the latest validated aggregate;
   the Home Assistant-side last-known-good calculation remains available.

Supplemental paths are stored as confined paths relative to `/config`. Filenames,
account identifiers, and depot numbers are not used as public source identities.

## DKB dated exports

Multiple configured files from the same DKB depot are treated as dated snapshots, not separate portfolios. Only the newest export date contributes. Different depots remain independent sources.

## Optional investment reserve in REST schema 1

A conforming local REST source may add this optional top-level object:

```json
{
  "investment_reserve": {
    "available_eur": "350.00",
    "as_of": "2026-08-01T00:00:00+02:00"
  }
}
```

Both fields are required when the object is present. `available_eur` must be a
canonical non-negative decimal string, and `as_of` must be a timezone-aware
bounded timestamp. Numeric JSON values, partial objects, negative amounts,
naive timestamps, and implausibly future timestamps are rejected.

The reserve is optional so existing REST sources remain schema-compatible. Its
absence does not invalidate the portfolio snapshot; it makes live-reserve-based
execution unavailable.
