# Portfolio Architect 1.19.0-rc2

Version 1.19.0-rc2 is an acceptance-informed correction release for the experimental
Comdirect brokerage diagnostics introduced in rc1. Portfolio Architect v1.18.0
remains the stable known-good baseline.

## Live acceptance findings

The rc1 diagnostics were tested against two current Comdirect ETF savings-plan
examples:

- `IE00BYWZ0333`, confirmed in the Comdirect UI with a 0.00% savings-plan fee;
- `IE00BJ0KDQ92`, configured with the regular 1.50% savings-plan fee.

Both instrument responses exposed the same potentially relevant metadata:

```text
fundFlags: []
fundStatus: null
regularIssueSurcharge: 0
reducedIssueSurcharge: 0
discountIssueSurcharge: 0
```

The fields therefore do not provide a usable current savings-plan promotion signal
for these live samples and remain opaque metadata only.

For quantity 1 at Tradegate, the ex-ante endpoint returned the same ordinary-order
purchase charges for both ETFs:

```text
Orderprovision:                               EUR 9.90
Börsenplatzabhängiges Entgelt:                EUR 2.50
Abwicklungsentgelt Clearstream/Streifband:    EUR 2.90
Total purchase costs:                         EUR 15.30
```

The live tests created no PhotoTAN challenge and no pending or open order appeared. The endpoint
is therefore retained only as an explicitly labelled ordinary-order cost diagnostic;
it is not a savings-plan quotation or promotion detector.

## Dashboard corrections

rc1 exposed two dashboard defects that are corrected in rc2:

- a normal tap on a recommended-buy tile now opens the copy-friendly ISIN entity;
- a long press opens the detailed purchase explanation;
- the conditional **Order identifiers / Orderkennungen** card now reads the seven
  actual proposed-buy entities instead of a non-existent aggregate
  `recommendations` attribute;
- only instruments with a positive proposed buy are listed.

The implementation remains native Home Assistant YAML without a custom card or
JavaScript dependency.

## Experimental brokerage diagnostics

The protected Gateway Ingress page retains two manual operations:

- read documented instrument metadata and eligible public venues;
- request one bounded ex-ante ordinary BUY/MARKET cost indication through
  `/api/brokerage/v3/orders/costindicationexante`.

The implementation contains no generic POST proxy and no order prevalidation,
validation, quote/ticket, brokerage TAN, submission, modification, cancellation, or
transaction-history operation. Probe state is process-local, sanitized, and absent
from REST portfolio schema 1, Gateway health schema 5, Home Assistant entities,
diagnostics, and scheduled refreshes.

## Fee-verification lifecycle

Optional `fee_verified_at`, `fee_source`, and
`fee_verification_max_age_days` fields remain supported. They provide a bounded
human-review reminder only. Diagnostics never overwrite `fee_pct` or verification
metadata automatically.

## Compatibility

- Portfolio payload schema 8 is unchanged.
- REST schema 1 is unchanged.
- Gateway health schema 5 is unchanged.
- Existing entity IDs and unique IDs are unchanged.
- Allocation, policy, target corridor, recommendation distribution, execution-cost
  calculation, and decision-trace semantics are unchanged.
- Existing v1.18.0 and rc1 configuration remains valid.
- No Gateway authentication, selected-account, or stored-session migration is
  required for an in-place App update.
