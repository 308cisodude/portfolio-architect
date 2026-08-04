# Portfolio Architect Gateway v1.19.0-rc1

This App package is an **experimental release candidate**. It preserves the
established live portfolio, investment-cash reserve, OAuth/session, cached snapshot,
REST portfolio schema 1, and health schema 5.

## Update in place

Do not uninstall the App and do not remove App-private data. An in-place update
preserves API credentials, OAuth/session state, Gateway bearer token, cached
snapshot, and the selected investment account. A new PhotoTAN bootstrap is needed
only when Comdirect rejects the existing session.

## Investment account

After authentication, open the App Web UI:

1. select **Discover investment accounts**;
2. review the bounded masked EUR-account choices;
3. select the dedicated investment/settlement account explicitly;
4. wait for the next successful portfolio refresh.

The Gateway publishes the lower non-negative value of booked balance and available
cash. It never publishes the account identifier or IBAN.

## Experimental fee probe

The Web UI also provides two manual probes:

1. enter an ISIN to read documented fund metadata, opaque `fundFlags`, and eligible
   public venue labels;
2. choose a masked depot, one returned venue, and a small positive unit quantity to
   request an ex-ante ordinary BUY/MARKET cost indication.

The page and sanitized JSON state explicitly that no order was validated or
submitted and that the response is not a savings-plan quotation.

The App has no order prevalidation, validation, quote/ticket, brokerage TAN,
submission, modification, cancellation, or generic brokerage POST operation.
Private depot and venue identifiers remain behind random in-memory tokens. Probe
results are not persisted or included in the public portfolio/health endpoints.

See `docs/COMDIRECT-FEE-PROBE.md` in the complete source release for the acceptance
and interpretation rules.
