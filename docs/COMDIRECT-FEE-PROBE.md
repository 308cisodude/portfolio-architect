# Experimental Comdirect brokerage diagnostics

## Purpose and accepted interpretation

The v1.19.0 release-candidate diagnostics answer two bounded questions:

1. What documented instrument metadata and eligible public venues does Comdirect
   expose for one ISIN?
2. What ordinary-order costs does Comdirect calculate for one bounded BUY/MARKET
   request without validating or submitting an order?

Live rc1 acceptance compared a confirmed 0.00% savings-plan ETF
`IE00BYWZ0333` with a regular 1.50% savings-plan ETF `IE00BJ0KDQ92`.
Both returned empty `fundFlags`, a null fund status, and zero regular/reduced/discount
issue-surcharge fields. These values are not treated as a promotion detector.

The ordinary-order cost endpoint returned the same EUR 15.30 Tradegate purchase-cost
structure for both instruments at quantity 1. It is useful as an account-specific
ordinary-order cost diagnostic, but it is not a savings-plan quotation.

## Endpoint allowlist

The Gateway adds only these documented operations:

```text
GET  /api/brokerage/v1/instruments/{ISIN}
      with-attr=fundDistribution
      with-attr=orderDimensions

POST /api/brokerage/v3/orders/costindicationexante
```

The POST path is a constant in the transport. The Ingress user cannot supply an API
path, HTTP method, side, order type, validity type, or arbitrary JSON document.

The generated request is fixed to:

```json
{
  "side": "BUY",
  "orderType": "MARKET",
  "validityType": "GFD",
  "bestEx": false
}
```

Only the token-resolved depot, probed ISIN, token-resolved eligible venue, and a
bounded positive unit quantity vary.

## Explicitly absent operations

The code contains no calls for:

```text
/api/brokerage/v3/orders/prevalidation
/api/brokerage/v3/orders/validation
/api/brokerage/v3/orders
/api/brokerage/v3/quotes
/api/brokerage/v3/quoteticket
order modification
order cancellation
```

There is no generic brokerage POST function exposed to the App controller or UI.

## Execution boundary

- Diagnostics are started manually through Home Assistant Ingress.
- CSRF protection and the existing Ingress source/user-header checks apply.
- They never run in the polling or manual portfolio-refresh path.
- Results live only in Gateway process memory until cleared or the App restarts.
- Results are not persisted in `/data`.
- Results are not included in public REST or health schemas.

## Sanitization

The downloadable JSON can include public instrument metadata, opaque flags, public
venue labels, requested unit quantity, bounded cost labels and amounts, currencies,
holding period, total costs, and timestamps.

It excludes internal depot/venue identifiers, customer and account metadata, OAuth
and qSession material, request headers, upstream links, inducement objects, raw
responses, and exception bodies.

## Interpretation rules

- `fundFlags`, fund status, and surcharge fields remain opaque observations.
- Empty or zero values must not be interpreted as 0% savings-plan eligibility.
- `ordinary_order_cost_indication` must never be presented as a savings-plan quote.
- Diagnostic results never update configured savings-plan fees automatically.
- Current savings-plan fees remain subject to human verification until Comdirect
  exposes a documented machine-readable contract for that information.

## Live safety acceptance

The rc1 live test completed both instrument reads and both ex-ante cost requests
without a PhotoTAN invocation and without creating a pending or open order. This
supports the endpoint contract but does not broaden the allowed operation set.
