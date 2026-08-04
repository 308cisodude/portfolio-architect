# Experimental Comdirect fee probe

## Purpose

The v1.19.0-rc1 probe collects bounded evidence for two questions:

1. Do documented `fundFlags` differ consistently between promoted and regular
   Comdirect ETF savings-plan products?
2. Does the documented ex-ante ordinary-order cost endpoint provide useful evidence
   for validating Portfolio Architect's manual-order cost assumptions?

It does not assume that ordinary-order costs describe a recurring savings plan.

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

- Probes are started manually through Home Assistant Ingress.
- CSRF protection and the existing Ingress source/user-header checks apply.
- They never run in the polling or manual portfolio-refresh path.
- Results live only in Gateway process memory until cleared or the App restarts.
- Probe results are not persisted in `/data`.
- Probe results are not included in public REST or health schemas.

## Sanitization

The downloadable JSON can include public instrument metadata, opaque flags, public
venue labels, requested unit quantity, bounded cost labels and amounts, currencies,
holding period, total costs, and timestamps.

It excludes internal depot/venue identifiers, customer and account metadata, OAuth
and qSession material, request headers, upstream links, inducement objects, raw
responses, and exception bodies.

## Interpretation rule

`fundFlags` are retained exactly as opaque strings and sorted for deterministic
comparison. No flag receives a semantic label until repeated promoted/regular
samples establish a stable distinction and an official contract or sufficiently
strong evidence supports that interpretation.

An ex-ante response is labelled `ordinary_order_cost_indication`. It must never be
presented as a savings-plan quotation merely because the tested instrument is
savings-plan eligible.
