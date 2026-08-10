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

## Optional authorized investment cash in REST schema 1

A conforming local REST source may continue to publish the established
compatibility object:

```json
{
  "investment_reserve": {
    "available_eur": "100",
    "as_of": "2026-08-10T20:59:00Z"
  }
}
```

Both fields are required when the object is present. `available_eur` is the amount
Portfolio Architect is authorized to allocate. It must be a canonical
non-negative decimal string; `as_of` must be a timezone-aware bounded timestamp.

Version 1.19.0 adds an optional explanatory object without changing the schema
version:

```json
{
  "investment_cash": {
    "account_balance_eur": "8601.53",
    "eligible_eur": "8601.53",
    "authorized_eur": "100",
    "policy": "capped",
    "cap_eur": "100",
    "as_of": "2026-08-10T20:59:00Z"
  }
}
```

`account_balance_eur` may be signed. The other amounts are non-negative. Policy is
`all_available` or `capped`; `cap_eur` is required only for `capped`. The
authorized amount may not exceed eligible cash and must equal eligible cash for
`all_available`, or `min(eligible_eur, cap_eur)` for `capped`.

When `investment_cash` is present, the compatibility `investment_reserve` object
is also required, with the same timestamp and an `available_eur` value equal to
`authorized_eur`. Portfolio Architect rejects inconsistent pairs. Older supported
REST sources may omit `investment_cash` entirely.

Numeric JSON values, partial objects, inconsistent policies, invalid decimals,
naive timestamps, and implausibly future timestamps are rejected.
