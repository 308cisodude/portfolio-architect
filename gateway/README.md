# Portfolio Architect Gateway runtime v1.60.0

Version 1.60.0 adds a bounded read-only helper that derives per-capability evidence clocks from the already-published canonical Gateway snapshot and displays them beside the existing health-schema-9 acquisition authority. The helper does not inspect inactive staged provider evidence and cannot mutate acquisition state. Health schema 9, schemas 1–8 compatibility, REST schema 1, provider authority and no-fallback semantics are unchanged.

Version 1.59.0 adds only common read-only operator presentation for the existing health-schema-9 acquisition authority and method status. Health schema 9, schemas 1–8 compatibility, REST schema 1, provider authority and no-fallback semantics are unchanged.

Version 1.55.0 keeps health schema 8 and REST schema 1 unchanged. Static `csv`/`pdf` acquisition snapshots are no longer expired by the live-source LKG cache TTL; their immutable evidence timestamps remain visible and Portfolio Architect applies the configured static freshness policy. Live acquisition methods retain the configured bounded cache age.

Version 1.53.0 adds provider-neutral health schema 8 acquisition-control metadata while retaining health schemas 1–7 and REST schema 1. The common server exposes only bounded method inventory/readiness, explicit no-fallback policy and operator switch history; provider-specific activation remains outside the common server.


Version 1.50.0 is package alignment for Portfolio Architect’s source-management UX milestone. Common Gateway runtime, health schema 7, REST schema 1 and provider acquisition behavior are unchanged from v1.49.0.

Version 1.48.1 is package alignment for Portfolio Architect’s Home Assistant-side acquisition-aware freshness correction. Common Gateway runtime, health schema 7, REST schema 1 and provider acquisition behavior are unchanged from v1.48.0.

Version 1.48.0 adds bounded health-schema-7 acquisition-mode reporting and the explicit Comdirect live/API versus static/CSV acquisition wrapper. REST portfolio schema 1, verified private-PKI HTTPS, bearer authentication and provider-neutral common runtime semantics remain intact.

The Gateway is a dedicated, Python-library-dependency-free service that converts one
provider-specific portfolio source into provider-neutral Portfolio Architect REST
schema 1. Version 1.24.0 introduces the common `PortfolioProvider` runtime contract
and Gateway health schema 6. The released provider implementation remains
Comdirect.

The common authenticated server no longer imports or type-depends on
`ComdirectClient`. It consumes only a bounded provider ID, the provider refresh
cadence, and validated provider-neutral snapshots. Comdirect OAuth/bootstrap,
account discovery, selected-account persistence, cash authorization and upstream
API behavior remain isolated in the Comdirect implementation.

The released Comdirect Home Assistant App is **Portfolio Architect Gateway — Comdirect** with canonical slug `portfolio_architect_gateway_comdirect`. The historical unqualified `portfolio_architect_gateway` package was withdrawn from the active repository in v1.57.0 after its final v1.56.x migration-source line; the canonical App still accepts the established bounded migration from an already-installed supported Legacy instance.

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
needs. Read-only enforcement therefore occurs in the implementation and container
boundary rather than by assuming bank-side token scoping.

## Provider identity and health

Gateway health schema 6 adds exactly one provider field: `provider_id`. The current
Comdirect implementation publishes `comdirect`. The identifier is bounded,
non-secret and carries no account/depot identity. Health schemas 1 through 5 remain
available unchanged for older Portfolio Architect versions.

The provider contract and official future App identities are documented in
`docs/GATEWAY-PROVIDERS.md`. The common runtime remains provider-neutral in v1.47.0;
provider-specific acquisition continues to live only in the corresponding App package.
The ISIN-first v1.26.1 hotfix is implemented in Portfolio Architect's Home Assistant calculation layer and does not change Gateway REST schema 1 or health schema 6. Version 1.47.0 retains the private-PKI HTTPS helper and v1.26.7 quantity-bearing cached-snapshot/ETag-precedence guarantees. Comdirect OAuth session maintenance is provider-specific; provider acquisition contracts and REST/health schemas are unchanged.

## Authorized investment cash

For every Comdirect refresh, the Gateway requires both booked balance and available
cash for the explicitly selected EUR account. It first computes **eligible cash**
as the lower value, clamped at zero. That prevents overdraft/credit facilities and
pending debits from increasing the advisory budget.

The Gateway then applies one authorization policy:

- `all_available`: authorize all eligible cash; this is the default and preserves
  the pre-1.19 behavior;
- `capped`: authorize no more than a configured EUR cap;
- `retain`: keep a configured EUR cash reserve untouched and authorize only
  `max(eligible - retain_eur, 0)`. The Ingress UI labels this **Keep cash reserve**.

Human cash-policy form input accepts common EUR decimal/grouping styles such as `1024,00`,
`1024.00`, `1.024,00` and `1,024.00`, plus validated space/apostrophe grouping. Accepted values are
normalized before persistence; malformed input returns bounded fixed guidance without replacing the
last valid private policy.

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

Use the native Home Assistant App bundle for the complete Comdirect workflow.
Update in place and never remove App data during a normal upgrade. Existing OAuth
state, Gateway bearer token, API credentials, cached snapshot, selected account,
and cash-policy state survive the v1.24.x provider-App refactor.
