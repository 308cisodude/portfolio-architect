# Portfolio Architect Gateway v1.19.1

The Gateway is a dedicated, dependency-free Python service that converts the
Comdirect depot API into provider-neutral Portfolio Architect REST schema 1.
Version 1.19.1 retains the provider-owned investment-cash authorization introduced in 1.19.0 and fixes the capped-to-all-available Ingress transition.

The released Home Assistant App provides the authenticated Ingress workflow for
account discovery, explicit account selection, cash-policy configuration, and
Comdirect bootstrap/reauthentication.

## Security boundary

The running service:

- exposes authenticated `GET /api/v1/portfolio` and optional authenticated
  `GET /healthz` only;
- contains no order, trading, transfer, payment, or account-transaction endpoint;
- uses only the bounded Comdirect read paths required for depots, positions,
  instrument metadata, and account balances;
- never reads the Comdirect username or password after bootstrap;
- persists OAuth/session material, the last validated snapshot, the explicitly
  selected private account identifier, and non-secret cash-policy state;
- never publishes the account identifier, IBAN, account label, account holder,
  credit limit, transaction history, or bank authentication material;
- fails closed on redirects, malformed amounts, invalid policy state, invalid
  JSON, duplicate identities, excessive pagination, oversized responses, or
  incomplete balance semantics.

The Comdirect OAuth token may contain broader brokerage scope than this service
needs. Read-only enforcement therefore occurs in the implementation and
container boundary rather than by assuming bank-side token scoping.

## Authorized investment cash

For every refresh, the Gateway requires both booked balance and available cash
for the explicitly selected EUR account. It first computes **eligible cash** as
the lower value, clamped at zero. That prevents overdraft/credit facilities and
pending debits from increasing the advisory budget.

The Gateway then applies one authorization policy:

- `all_available`: authorize all eligible cash; this is the default and preserves
  the pre-1.19 behavior;
- `capped`: authorize no more than a configured EUR cap.

The public snapshot retains the compatibility object and adds bounded metadata:

```json
{
  "investment_reserve": {
    "available_eur": "100",
    "as_of": "2026-08-10T20:59:00Z"
  },
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

`investment_reserve.available_eur` always equals `authorized_eur`. This preserves
compatibility with older Portfolio Architect releases while allowing new releases
to explain why the authorized amount differs from the account balance.

The bounded numeric account balance is intentionally provider-neutral metadata;
no account identifier or source balance document leaves the Gateway.

Ingress form state is not a security boundary. When `all_available` is selected,
the server canonicalizes any stale submitted cap away before persistence. Capped
mode still requires a valid cap, and malformed persisted policy files fail closed.

## Deployment

Use the native Home Assistant App bundle for the complete workflow. Update in
place and never remove App data during a normal upgrade. Existing OAuth state,
Gateway bearer token, API credentials, cached snapshot, selected account, and
cash-policy state survive an in-place update.
