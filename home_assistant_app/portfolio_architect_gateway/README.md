# Portfolio Architect Gateway v1.19.0-rc2

Version 1.19.0-rc2 is an experimental brokerage-diagnostic correction release. The
established live portfolio, reserve, OAuth/session, REST portfolio schema 1, and
health schema 5 remain compatible.

The protected admin Ingress UI provides:

- a documented instrument metadata read for opaque `fundFlags`, surcharge fields,
  and eligible public venues;
- a documented non-submitting ex-ante ordinary-order cost indication.

Live rc1 acceptance compared a confirmed 0% and a regular 1.5% Comdirect ETF
savings plan. The instrument metadata did not differ, and the ex-ante endpoint
returned the same ordinary-order charges. These operations are therefore diagnostics,
not a savings-plan promotion detector or quotation.

The transport permits only the exact cost-indication path. It contains no order
prevalidation, validation, quote/TAN, submission, modification, cancellation, or
generic brokerage POST facility. Results are sanitized, process-local, and absent
from the public portfolio and health endpoints.

## Security boundary

The running service:

- exposes authenticated `GET /api/v1/portfolio` and optional authenticated
  `GET /healthz` only;
- binds served snapshots to SHA-256, ETag, and position-count metadata;
- has no public order, order-book, trading, transfer, payment, or account-transaction
  endpoint;
- contains a bounded outbound allowlist for OAuth/session activation, required
  portfolio/account reads, the explicit instrument metadata read, and exactly one
  non-submitting ex-ante cost-indication POST;
- never reads the Comdirect username or password after bootstrap;
- persists OAuth/session material, the last provider-neutral snapshot, and—only
  after explicit App selection—the private account identifier;
- never logs credentials, bearer tokens, cookies, account identifiers, instrument
  names, quantities, or monetary values;
- fails closed on redirects, malformed/non-EUR amounts, invalid JSON, duplicate
  identities, excessive pagination, oversized responses, or incomplete balance
  semantics.

The Comdirect OAuth token may contain broader brokerage scope than this service
needs. Non-submission is enforced by the implementation and deployment boundary.

## Investment-reserve semantics

The App discovers eligible EUR accounts only after an authenticated session is
available. The user explicitly chooses a masked account. The account identifier
stays in App-private storage.

For every refresh, the Gateway requires both the booked balance and available cash
for that account. It publishes the lower value, clamped at zero, as the usable
investment reserve. No IBAN, account number, account label, transaction, credit
limit, or raw balance document is published.

## Deployment

Use the native Home Assistant App bundle for the account-selection and diagnostic
workflows. Update in place and never remove App data during a normal upgrade.
Existing OAuth state, Gateway bearer token, API credentials, cached snapshot, and
selected account survive an in-place update.
