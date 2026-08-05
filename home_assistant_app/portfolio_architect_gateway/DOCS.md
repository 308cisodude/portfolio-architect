# Portfolio Architect Gateway v1.19.0-rc2

This App package is an **experimental release candidate**. It preserves the
established live portfolio, investment-cash reserve, OAuth/session, cached snapshot,
REST portfolio schema 1, and health schema 5.

## Update in place

Do not uninstall the App and do not remove App-private data. An in-place update
preserves API credentials, OAuth/session state, Gateway bearer token, cached
snapshot, and selected investment account. A new PhotoTAN bootstrap is needed only
when Comdirect rejects the existing session.

## Investment account

After authentication, open the App Web UI, discover eligible EUR accounts, and
select the dedicated investment/settlement account explicitly. The Gateway publishes
the lower non-negative value of booked balance and available cash. It never
publishes the account identifier or IBAN.

## Experimental brokerage diagnostics

The Web UI provides two manual diagnostics:

1. enter an ISIN to read documented instrument metadata and eligible public venues;
2. choose a masked depot, one returned venue, and a positive unit quantity to
   request an ex-ante ordinary BUY/MARKET cost indication.

Live rc1 acceptance found that a confirmed 0% and a regular 1.5% savings-plan ETF
returned the same empty `fundFlags`, null fund status, zero surcharge fields, and
the same ordinary-order purchase-cost structure. Neither diagnostic is a current
savings-plan promotion detector.

The page and sanitized JSON state explicitly that no order was validated or
submitted and that the response is not a savings-plan quotation. The App has no
order prevalidation, validation, quote/ticket, brokerage TAN, submission,
modification, cancellation, or generic brokerage POST operation.

Private depot and venue identifiers remain behind random in-memory tokens. Results
are not persisted or included in the public portfolio/health endpoints.

See `docs/COMDIRECT-FEE-PROBE.md` in the complete source release for the accepted
interpretation and safety boundary.
