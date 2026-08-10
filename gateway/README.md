# Portfolio Architect Gateway v1.18.2

The gateway is a dedicated, dependency-free Python service that converts the
Comdirect depot API into Portfolio Architect REST schema 1. Version 1.16.0 added
an optional, privacy-bounded investment-reserve path for the native Home
Assistant App deployment.

The standalone deployment remains suitable for the existing read-only portfolio
snapshot. Account discovery and explicit settlement-account selection are
intentionally delivered through the authenticated Home Assistant App Ingress UI
in this release; a standalone gateway without that private selection state omits
the optional investment reserve.

## Security boundary

The running service:

- exposes authenticated `GET /api/v1/portfolio` and optional authenticated
  `GET /healthz` only;
- binds served snapshots to SHA-256, ETag, and position-count metadata;
- has no order, order-book, trading, transfer, payment, or account-transaction
  endpoint;
- contains a bounded outbound allowlist for OAuth/session activation and the
  read paths required for depots, positions, instrument metadata, and account
  balances;
- never reads the Comdirect username or password after bootstrap;
- persists OAuth/session material, the last provider-neutral snapshot, and—only
  after explicit App selection—the private account identifier;
- never logs credentials, bearer tokens, cookies, account identifiers,
  instrument names, quantities, or monetary values;
- fails closed on redirects, malformed/non-EUR amounts, invalid JSON, duplicate
  identities, excessive pagination, oversized responses, or incomplete balance
  semantics.

The Comdirect OAuth token may contain broader brokerage scope than this service
needs. Read-only enforcement therefore occurs in the implementation and
deployment boundary rather than through an assumption about token scope.

## Investment-reserve semantics

The App discovers eligible EUR accounts only after an authenticated session is
available. The user explicitly chooses a masked account. The account identifier
stays in App-private storage.

For every refresh, the Gateway requires both the booked balance and the available
cash value for that selected account. It publishes the lower value, clamped at
zero, as the usable investment reserve. This prevents credit facilities and
pending debits from inflating the advisory purchase budget.

The public snapshot contains only:

```json
{
  "investment_reserve": {
    "available_eur": "350.00",
    "as_of": "2026-08-01T00:00:00+02:00"
  }
}
```

No IBAN, account number, account label, transaction, credit limit, or raw balance
document is published.

## Deployment

Use the native Home Assistant App bundle for the account-selection workflow.
Update in place and never remove App data during a normal upgrade. Existing OAuth
state, Gateway bearer token, API credentials, cached snapshot, and selected
account survive an in-place update.

The selected-account reserve semantics were validated live before the v1.17.1
publication milestone and remain unchanged in v1.18.2. The Gateway runtime
remains unchanged from v1.16.0.
