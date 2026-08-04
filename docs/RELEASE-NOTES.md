# Portfolio Architect 1.19.0-rc1

Version 1.19.0-rc1 is an experimental Comdirect fee-discovery release candidate.
It preserves the v1.18.0 portfolio calculation and Plan Delta & Decision Trace,
while adding two explicit admin-only probes to the Gateway App and a small Home
Assistant fee-review workflow.

## Experimental Comdirect probes

The protected Gateway Ingress page can now perform two manual operations:

- read one instrument through the documented instrument endpoint with
  `fundDistribution` and `orderDimensions`, retaining `fundFlags` as opaque values;
- request an ex-ante cost indication for one bounded ordinary BUY/MARKET order
  through `/api/brokerage/v3/orders/costindicationexante`.

The implementation contains no generic POST proxy. It has no brokerage order
validation, prevalidation, quote, TAN, submission, modification, cancellation, or
transaction-history operation. The cost probe is explicitly labelled as an
ordinary-order indication, not a savings-plan quotation.

Probe execution is manual and available only through Home Assistant Ingress. It is
not part of scheduled portfolio refreshes and is not exposed through REST portfolio
schema 1 or Gateway health schema 5.

## Bounded and sanitized evidence

The instrument probe retains only:

- ISIN, public name and WKN;
- opaque `fundFlags`, fund status, currency, and bounded surcharge fields;
- public venue name, country, and type;
- probe timestamp.

Private depot and venue identifiers are represented by short-lived random tokens in
the browser and are absent from the displayed/downloaded result. The cost result
retains bounded cost groups, labels, amounts, currencies, holding-period assumption,
and total costs. It excludes depot IDs, venue IDs, OAuth/session material,
inducements, links, and raw upstream responses.

## Fee-verification lifecycle

A plan may opt into fee-review freshness by configuring:

```yaml
broker:
  fee_verification_max_age_days: 90
  savings_plans:
    IE00BJ0KDQ92:
      available: true
      fee_pct: 1.5
      fee_verified_at: 2026-08-03
      fee_source: manual_comdirect_verification
```

When enabled, Portfolio Architect emits an informational policy finding if a target
instrument has no valid verification date/source, if the date lies in the future,
or if it is older than the configured maximum age. Probe results never overwrite
`fee_pct` or verification metadata automatically.

## Copyable order identifiers

The supplied English/German dashboard adds a conditional built-in Markdown block
listing only current recommended-buy ISINs as selectable text. Existing purchase
tiles and their tap/hold actions remain available.

## Release-candidate boundary

This release requires the v1.19.0-rc1 Gateway App for probe testing. The App package
is marked `experimental`. No Comdirect test environment is available, so the probe
contracts require acceptance against a real account before any stable release.

## Compatibility

- Portfolio payload schema 8 remains unchanged.
- REST schema 1 remains unchanged.
- Gateway health schema 5 remains unchanged.
- Existing entity IDs and unique IDs remain unchanged.
- Allocation, policy thresholds, target corridor, recommendation distribution,
  execution-cost calculations, and decision-trace semantics remain unchanged.
- Existing v1.18.0 configuration remains valid; fee-verification metadata is opt-in.
- No Gateway authentication or selected-account migration is required for an
  in-place App update.
